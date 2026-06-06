"""Chat turn handling with guardrails and curriculum-scoped system prompt."""
from __future__ import annotations

import json
import pathlib
from typing import AsyncGenerator
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MessageRole
from app.domain.exceptions import ExamNotFound
from app.infra.llm.claude import stream_claude
from app.infra.vault import AppSecrets
from app.repositories import message_repo
from app.services import guardrails_service

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
    async for chunk in stream_claude(claude_messages, system=system, api_key=secrets.anthropic_api_key):
        if chunk == "data: [DONE]\n\n":
            break
        yield chunk
        try:
            payload = json.loads(chunk[6:])
            if payload.get("event") == "token":
                full_response += payload.get("text", "")
        except (json.JSONDecodeError, IndexError):
            pass

    if tier == "warning":
        yield f"data: {json.dumps({'event': 'guardrail_warning', 'message': _WARNING_SUFFIX})}\n\n"

    yield f"data: {json.dumps({'event': 'done'})}\n\n"
    yield "data: [DONE]\n\n"

    await message_repo.add_message(
        db_session, conv.id, MessageRole.assistant, full_response
    )
    await db_session.commit()
