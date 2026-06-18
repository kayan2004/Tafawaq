"""Chat turn handling with guardrails and curriculum-scoped system prompt."""
from __future__ import annotations

import asyncio
import base64
import json
import pathlib
from typing import AsyncGenerator
from uuid import UUID

import asyncpg
import pgvector.asyncpg
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MessageRole
from app.infra import langfuse_client
from app.infra.llm.claude import call_claude, call_claude_vision, stream_claude
from app.infra.llm.tools import RETRIEVE_TEXTBOOK_PAGE_TOOL
from app.infra.vault import AppSecrets
from app.repositories import exam_repo, message_repo, textbook_repo
from app.services import guardrails_service, retrieval_service
from prompts.math.chat import BLOCK_MESSAGE as _BLOCK_MESSAGE
from prompts.math.chat import IMAGE_EXTRACT_PROMPT as _IMAGE_EXTRACT_PROMPT
from prompts.math.chat import RETRIEVE_SYSTEM_PROMPT as _RETRIEVE_SYSTEM_PROMPT
from prompts.math.chat import WARNING_SUFFIX as _WARNING_SUFFIX
from prompts.math.chat import build_chat_system_prompt as _build_chat_system_prompt_fn
from prompts.shared.chat import build_retrieve_user_message as _build_retrieve_user_message

_CHAT_TOOLS = [RETRIEVE_TEXTBOOK_PAGE_TOOL]

_RETRIEVE_PREFIX = "/retrieve "

_curriculum: dict = json.loads(
    (pathlib.Path(__file__).parent.parent / "data" / "curriculum.json").read_text()
)


def _build_chat_system_prompt(counter: int) -> str:
    return _build_chat_system_prompt_fn(_curriculum, counter)


_SUBJECT = "math_gs12"


async def _build_exam_context(
    db_session: AsyncSession,
    session_id: UUID,
    user_id: UUID,
) -> str | None:
    exam = await exam_repo.get_session(db_session, session_id)
    if exam is None or exam.user_id != user_id:
        return None

    lines: list[str] = [
        "## Attached Exam\n",
        f"Type: {exam.session_type.value}  |  Status: {exam.status.value}  |  Date: {exam.created_at.strftime('%Y-%m-%d')}\n",
    ]

    for ex in exam.exam_content.get("exercises", []):
        lines.append(f"\n### Exercise {ex['id']} — {ex.get('topic', '')} ({ex.get('total_marks', '?')} marks)")
        lines.append(ex.get("content", ""))
        for p in ex.get("parts", []):
            lines.append(f"  Part {p['part']} ({p.get('marks', '?')} marks): {p.get('content', '')}")

    result = await exam_repo.get_result(db_session, session_id)
    if result is not None:
        lines.append("\n### Student Answers")
        for ex_ans in result.student_answers.get("answers", []):
            lines.append(f"\nExercise {ex_ans.get('exercise_id')}:")
            for p in ex_ans.get("parts", []):
                lines.append(f"  Part {p['part']}: {p.get('answer', '(blank)')}")

        ev = result.evaluator_1
        avg = round((result.total_score_1 + result.total_score_2) / 2, 1)
        lines.append(f"\n### Grading Results (avg {avg}/{ev.get('grand_max', 20)})")
        for ex_res in ev.get("exercises", []):
            lines.append(
                f"\nExercise {ex_res.get('exercise_id')}: "
                f"{ex_res.get('exercise_total', 0):.1f}/{ex_res.get('exercise_max', 0):.0f}"
            )
            for part_id, pd in ex_res.get("parts", {}).items():
                lines.append(
                    f"  Part {part_id}: {pd.get('score', 0)}/{pd.get('max_score', 0)} — {pd.get('feedback', '')}"
                )
                if pd.get("correction"):
                    lines.append(f"    Correction: {pd['correction']}")

    return "\n".join(lines)


async def clear_chat(
    conversation_id: UUID,
    db_session: AsyncSession,
    redis: Redis,
) -> None:
    conv_id = await message_repo.clear_conversation(db_session, conversation_id)
    await db_session.commit()
    if conv_id is not None:
        await guardrails_service.reset_counter(redis, str(conv_id))


async def handle_turn(
    message: str,
    conversation_id: UUID,
    user_id: UUID,
    secrets: AppSecrets,
    db_session: AsyncSession,
    redis: Redis,
    is_admin: bool = False,
    attached_session_id: UUID | None = None,
    image_base64: str | None = None,
    image_media_type: str | None = None,
) -> AsyncGenerator[str, None]:
    # Open our own asyncpg connection for the generator's lifetime.
    # Cannot use Depends(get_db_conn) here: FastAPI closes dependencies when the
    # route handler *returns* the StreamingResponse, before any yielding occurs.
    _db_url = secrets.db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(_db_url)
    await pgvector.asyncpg.register_vector(conn)
    try:
        await message_repo.add_message(db_session, conversation_id, MessageRole.user, message)
        await db_session.commit()

        if message == "/retrieve" or message.startswith(_RETRIEVE_PREFIX):
            query = message[len("/retrieve"):].strip()
            if image_base64 and image_media_type:
                try:
                    image_bytes = base64.b64decode(image_base64)
                    image_extract_prompt = langfuse_client.get_prompt(
                        secrets, "chat_image_extract_prompt", fallback=_IMAGE_EXTRACT_PROMPT
                    )
                    extracted = await asyncio.to_thread(
                        call_claude_vision,
                        image_bytes,
                        image_media_type,
                        image_extract_prompt,
                        secrets.anthropic_api_key,
                        secrets,
                        1024,
                        trace_name="retrieve_image_extract",
                        user_id=str(user_id),
                        session_id=str(conversation_id),
                    )
                    extracted = extracted.strip()
                    if extracted:
                        query = extracted + ("\n\n" + query if query else "")
                except Exception:
                    pass  # degrade: continue with text query only
            matches: list[dict] = []
            if query:
                candidates = await retrieval_service.retrieve_past_questions(
                    query=query,
                    topic=None,
                    question_type=None,
                    year_from=None,
                    year_to=None,
                    limit=6,
                    secrets=secrets,
                    conn=conn,
                )
                if candidates:
                    candidate_dicts = [
                        {
                            "year": q.year,
                            "session": q.session,
                            "marks": q.marks,
                            "content": q.content,
                        }
                        for q in candidates
                    ]
                    retrieve_system_prompt = langfuse_client.get_prompt(
                        secrets, "chat_retrieve_system_prompt", fallback=_RETRIEVE_SYSTEM_PROMPT
                    )
                    raw = await asyncio.to_thread(
                        call_claude,
                        [{"role": "user", "content": _build_retrieve_user_message(query, candidate_dicts)}],
                        retrieve_system_prompt,
                        secrets.anthropic_api_key,
                        secrets,
                        3000,
                        trace_name="retrieve_filter",
                        user_id=str(user_id),
                        session_id=str(conversation_id),
                    )
                    # Parse defensively: strip markdown fences, find outermost {}
                    try:
                        text = raw.strip()
                        if text.startswith("```"):
                            lines = text.splitlines()
                            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                        start = text.find("{")
                        end = text.rfind("}") + 1
                        parsed = json.loads(text[start:end]) if start != -1 and end > start else {}
                        raw_matches = parsed.get("matches", [])
                        matches = raw_matches if isinstance(raw_matches, list) else []
                    except (json.JSONDecodeError, ValueError):
                        matches = []

            payload = json.dumps({"event": "retrieve_result", "matches": matches})
            yield f"data: {payload}\n\n"
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            yield "data: [DONE]\n\n"
            await message_repo.add_message(db_session, conversation_id, MessageRole.assistant, payload)
            await db_session.commit()
            return

        off_topic = await guardrails_service.classify_message(message)
        counter = await guardrails_service.get_counter(redis, str(conversation_id))

        if off_topic:
            counter = await guardrails_service.increment_counter(redis, str(conversation_id))
        else:
            await guardrails_service.reset_counter(redis, str(conversation_id))
            counter = 0

        tier = guardrails_service.get_guardrail_tier(counter)

        if tier == "block":
            yield f"data: {json.dumps({'event': 'guardrail_block', 'message': _BLOCK_MESSAGE})}\n\n"
            yield "data: [DONE]\n\n"
            return

        history = await message_repo.get_messages(db_session, conversation_id, limit=20)
        claude_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in history
        ]

        system = _build_chat_system_prompt(counter)
        if attached_session_id is not None:
            exam_ctx = await _build_exam_context(db_session, attached_session_id, user_id)
            if exam_ctx:
                system += f"\n\n{exam_ctx}"

        full_response = ""
        for _ in range(4):  # cap prevents runaway tool-call cycles
            text_this_round = ""
            tool_uses: list[dict] = []

            async for chunk in stream_claude(
                claude_messages,
                system=system,
                api_key=secrets.anthropic_api_key,
                secrets=secrets,
                tools=_CHAT_TOOLS,
                trace_name="chat_turn",
                user_id=str(user_id),
                session_id=str(conversation_id),
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
                        if is_admin:
                            yield chunk  # admin-only: expose tool calls in the chat UI
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
            db_session, conversation_id, MessageRole.assistant, full_response
        )
        await db_session.commit()
    finally:
        await conn.close()
