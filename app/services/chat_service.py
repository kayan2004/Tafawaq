"""Chat turn handling with guardrails and curriculum-scoped system prompt."""
from __future__ import annotations

import json
import pathlib
from typing import AsyncGenerator
from uuid import UUID

import asyncpg
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MessageRole
from app.domain.exceptions import ExamNotFound
from app.infra.llm.claude import stream_claude
from app.infra.llm.tools import RETRIEVE_TEXTBOOK_PAGE_TOOL, RETRIEVE_TEXTBOOK_SECTIONS_TOOL
from app.infra.vault import AppSecrets
from app.repositories import message_repo, textbook_repo
from app.services import guardrails_service, retrieval_service

_CHAT_TOOLS = [RETRIEVE_TEXTBOOK_PAGE_TOOL, RETRIEVE_TEXTBOOK_SECTIONS_TOOL]

_curriculum: dict = json.loads(
    (pathlib.Path(__file__).parent.parent / "data" / "curriculum.json").read_text()
)

_BLOCK_MESSAGE = (
    "I am designed specifically for Lebanese GS Grade 12 Math exam preparation. "
    "I cannot help with topics outside the official Lebanese baccalaureate math curriculum. "
    "Please ask me about calculus, functions, complex numbers, integrals, probability, "
    "geometry, or any other in-scope math topic!"
)

_WARNING_SUFFIX = (
    "Tip: I am most helpful when focused on Lebanese GS Math exam preparation topics "
    "such as functions, integrals, derivatives, probability, and geometry in space."
)


def _build_chat_system_prompt(counter: int) -> str:
    in_scope = ", ".join(_curriculum["in_scope"])
    out_of_scope = ", ".join(_curriculum["out_of_scope"])
    redirect_note = (
        "\n\nIMPORTANT: The student has been asking off-topic questions. Gently redirect "
        "every response back to Lebanese GS Math exam content."
        if counter == 2
        else ""
    )
    return f"""You are an expert Lebanese GS Grade 12 Math exam coach helping students prepare for the official Lebanese Baccalaureate exam.

CURRICULUM ({_curriculum['academic_year']}):
In-scope topics: {in_scope}
Out-of-scope (decline politely if asked): {out_of_scope}

GUIDELINES:
- Ground all explanations in the Lebanese official exam context and style.
- Use LaTeX notation for mathematical expressions.
- Reference past Lebanese baccalaureate exam exercises when relevant.
- Be encouraging and pedagogically clear.
- If a student asks about an out-of-scope topic, politely explain it is outside the Lebanese GS curriculum and redirect to in-scope content.{redirect_note}"""


async def handle_turn(
    conversation_id: UUID | None,
    message: str,
    user_id: UUID,
    secrets: AppSecrets,
    db_session: AsyncSession,
    redis: Redis,
    conn: asyncpg.Connection,
) -> AsyncGenerator[str, None]:
    if conversation_id is None:
        conv = await message_repo.create_conversation(db_session, user_id)
        await db_session.commit()
        yield f"data: {json.dumps({'event': 'conversation_id', 'conversation_id': str(conv.id)})}\n\n"
    else:
        conv = await message_repo.get_conversation(db_session, conversation_id)
        if conv is None or conv.user_id != user_id:
            raise ExamNotFound(f"Conversation {conversation_id} not found.")

    await message_repo.add_message(db_session, conv.id, MessageRole.user, message)
    await db_session.commit()

    off_topic = await guardrails_service.classify_message(message)
    counter = await guardrails_service.get_counter(redis, str(conv.id))

    if off_topic:
        counter = await guardrails_service.increment_counter(redis, str(conv.id))
    else:
        await guardrails_service.reset_counter(redis, str(conv.id))
        counter = 0

    tier = guardrails_service.get_guardrail_tier(counter)

    if tier == "block":
        yield f"data: {json.dumps({'event': 'guardrail_block', 'message': _BLOCK_MESSAGE})}\n\n"
        yield "data: [DONE]\n\n"
        return

    history = await message_repo.get_messages(db_session, conv.id, limit=20)
    claude_messages = [
        {"role": msg.role.value, "content": msg.content}
        for msg in history
    ]

    system = _build_chat_system_prompt(counter)

    full_response = ""
    for _ in range(4):  # cap prevents runaway tool-call cycles
        text_this_round = ""
        tool_uses: list[dict] = []

        async for chunk in stream_claude(
            claude_messages,
            system=system,
            api_key=secrets.anthropic_api_key,
            tools=_CHAT_TOOLS,
        ):
            if chunk == "data: [DONE]\n\n":
                break
            try:
                payload = json.loads(chunk[6:])
                event = payload.get("event")
                if event == "token":
                    text_this_round += payload.get("text", "")
                    yield chunk
                elif event == "tool_use":
                    tool_uses.append(payload)
                    # tool_use events are internal; never forwarded to the client
            except (json.JSONDecodeError, IndexError):
                pass

        full_response += text_this_round

        if not tool_uses:
            break  # end_turn — no more tool calls

        # Reconstruct the assistant message for the re-call
        assistant_content: list[dict] = []
        if text_this_round:
            assistant_content.append({"type": "text", "text": text_this_round})
        for tu in tool_uses:
            assistant_content.append({
                "type": "tool_use",
                "id": tu["tool_use_id"],
                "name": tu["name"],
                "input": tu["input"],
            })
        claude_messages.append({"role": "assistant", "content": assistant_content})

        tool_results: list[dict] = []
        for tu in tool_uses:
            if tu["name"] == "retrieve_textbook_page":
                page_number = tu["input"].get("page_number")
                page = await textbook_repo.get_page_by_number(db_session, page_number)
                if page is not None:
                    yield f"data: {json.dumps({'event': 'textbook_page', 'page_number': page.page_number, 'chapter': page.chapter, 'section': page.section})}\n\n"
                    result_content = json.dumps({
                        "page_number": page.page_number,
                        "chapter": page.chapter,
                        "section": page.section,
                        "page_type": page.page_type,
                        "content": page.content,
                    })
                else:
                    result_content = json.dumps(
                        {"error": f"Page {page_number} not found in the textbook."}
                    )
            elif tu["name"] == "retrieve_textbook_sections":
                query = tu["input"].get("query", "")
                source_types_arg = tu["input"].get("source_types")
                limit_arg = int(tu["input"].get("limit", 5))
                sections = await retrieval_service.retrieve_textbook_sections(
                    query=query,
                    source_types=source_types_arg,
                    limit=limit_arg,
                    secrets=secrets,
                    conn=conn,
                )
                if sections:
                    sections_meta = [
                        {
                            "chunk_id": str(s.chunk_id),
                            "chapter": s.chapter,
                            "section": s.section,
                            "source_type": s.source_type,
                            "page_start": s.page_start,
                            "page_end": s.page_end,
                        }
                        for s in sections
                    ]
                    yield f"data: {json.dumps({'event': 'textbook_sections', 'sections': sections_meta})}\n\n"
                    result_content = json.dumps({
                        "sections": [
                            {
                                "chunk_id": str(s.chunk_id),
                                "chapter": s.chapter,
                                "section": s.section,
                                "source_type": s.source_type,
                                "page_start": s.page_start,
                                "page_end": s.page_end,
                                "topic": s.topic,
                                "subtopic": s.subtopic,
                                "content": s.content,
                                "similarity": s.similarity,
                            }
                            for s in sections
                        ]
                    })
                else:
                    result_content = json.dumps({"sections": []})
            else:
                result_content = json.dumps({"error": f"Unknown tool: {tu['name']}"})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu["tool_use_id"],
                "content": result_content,
            })

        claude_messages.append({"role": "user", "content": tool_results})

    if tier == "warning":
        yield f"data: {json.dumps({'event': 'guardrail_warning', 'message': _WARNING_SUFFIX})}\n\n"

    yield f"data: {json.dumps({'event': 'done'})}\n\n"
    yield "data: [DONE]\n\n"

    await message_repo.add_message(
        db_session, conv.id, MessageRole.assistant, full_response
    )
    await db_session.commit()
