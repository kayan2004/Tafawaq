"""Exam generation, session management, and background validation."""
from __future__ import annotations

import asyncio
import json
import pathlib
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import GuardrailCategory, GuardrailDirection, GuardrailLevel, GuardrailSource, SessionStatus, SessionType
from app.domain.exceptions import ExamNotFound, ExtractionFailed
from app.domain.models import AnswerKey, ExamContent, ExamSession
from app.infra import langfuse_client
from app.infra.llm.claude import call_claude, call_claude_vision
from app.infra.redis_client import set_session
from app.infra.vault import AppSecrets
from app.repositories import exam_repo, message_repo
from app.services import guardrails_service

from prompts.math.exam_generation import (
    REGENERATE_SYSTEM_PROMPT as _REGENERATE_SYSTEM,
    VALIDATOR_SYSTEM_PROMPT as _VALIDATOR_SYSTEM,
    build_generation_system_prompt as _build_gen_prompt_fn,
)
from prompts.shared.exam_generation import JUDGE_SYSTEM_PROMPT as _JUDGE_SYSTEM
from app.utils import parse_json_response as parse_generation_response
from prompts.shared.extraction import build_extraction_prompt

# Load data files once at module import.
_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
_curriculum: dict = json.loads((_DATA_DIR / "curriculum.json").read_text())
_exam_config: dict = json.loads((_DATA_DIR / "exam_config.json").read_text())
_exam_analysis: dict = json.loads((_DATA_DIR / "exam_analysis.json").read_text())

_few_shot_exams: list[str] = []
_fs_exam = _DATA_DIR / "2021_regular_exam.md"
if _fs_exam.exists():
    _few_shot_exams.append(_fs_exam.read_text())

# Holds strong references to background tasks so GC cannot collect them mid-run.
_bg_tasks: set[asyncio.Task] = set()

# Lazy singleton sessionmaker for background tasks (separate from request-scoped DI).
_bg_engine = None
_bg_maker = None


def _get_bg_maker(db_url: str):
    global _bg_engine, _bg_maker
    if _bg_maker is None:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        _bg_engine = create_async_engine(db_url, echo=False)
        _bg_maker = async_sessionmaker(_bg_engine, expire_on_commit=False)
    return _bg_maker


# ── Generation helpers ────────────────────────────────────────────────────────

def _build_generation_system_prompt() -> str:
    return _build_gen_prompt_fn(_curriculum, _exam_analysis, _exam_config, _few_shot_exams)


def _build_generation_user_message(generation_prompt: str | None) -> str:
    brief = (
        generation_prompt.strip()
        if generation_prompt and generation_prompt.strip()
        else "Generate a full 20-point Lebanese GS Math mock exam covering a representative spread of the curriculum."
    )
    return (
        "Generate a 20-point Lebanese GS Mathematics mock exam from this student brief.\n\n"
        "Student exam brief:\n"
        f"{brief}\n\n"
        "Remember: the brief may narrow topic focus or difficulty, but the final exam must obey the system "
        "curriculum, Lebanese GS style, mark total, and JSON schema."
    )


def _expected_total_marks() -> float:
    return float(_exam_config.get("total_marks", 20) or 20)


def _validate_generated_payload(exam_content: ExamContent, answer_key: AnswerKey) -> None:
    """Validate model-output invariants that Pydantic shape checks cannot express."""
    errors: list[str] = []
    expected_total = _expected_total_marks()
    exercises = exam_content.exercises

    if not exercises:
        errors.append("exam has no exercises")
    total = sum(float(ex.total_marks) for ex in exercises)
    if abs(total - expected_total) > 0.01:
        errors.append(f"exam total is {total:g}, expected {expected_total:g}")

    exercise_ids = [ex.id for ex in exercises]
    if len(exercise_ids) != len(set(exercise_ids)):
        errors.append("exercise IDs must be unique")

    answer_by_id = {ex.id: ex for ex in answer_key.exercises}
    answer_ids = [ex.id for ex in answer_key.exercises]
    if len(answer_ids) != len(set(answer_ids)):
        errors.append("answer key exercise IDs must be unique")
    if set(answer_by_id) != set(exercise_ids):
        errors.append("answer key exercise IDs must match exam exercise IDs")

    for ex in exercises:
        if not ex.parts:
            errors.append(f"exercise {ex.id} has no parts")
            continue
        part_ids = [part.part for part in ex.parts]
        if len(part_ids) != len(set(part_ids)):
            errors.append(f"exercise {ex.id} part labels must be unique")
            continue
        part_total = sum(float(part.marks) for part in ex.parts)
        if abs(part_total - float(ex.total_marks)) > 0.01:
            errors.append(
                f"exercise {ex.id} part marks sum to {part_total:g}, expected {float(ex.total_marks):g}"
            )

        answer_ex = answer_by_id.get(ex.id)
        if answer_ex is None:
            continue
        part_marks = {part.part: float(part.marks) for part in ex.parts}
        answer_part_ids = [part.part for part in answer_ex.parts]
        if len(answer_part_ids) != len(set(answer_part_ids)):
            errors.append(f"answer key parts for exercise {ex.id} must be unique")
            continue
        answer_parts = {part.part: part for part in answer_ex.parts}
        if set(answer_parts) != set(part_marks):
            errors.append(f"answer key parts for exercise {ex.id} must match exam parts")
            continue
        for part_id, marks in part_marks.items():
            if abs(float(answer_parts[part_id].marks) - marks) > 0.01:
                errors.append(f"answer key mark mismatch for exercise {ex.id} part {part_id}")

    if errors:
        raise ValueError("; ".join(errors))


# ── Validation helpers (sync — all called via asyncio.to_thread) ──────────────

def _call_validator(question_text: str, api_key: str, secrets: AppSecrets, session_id: str | None = None) -> str:
    """Student-persona call: solve the question. Returns free-form solution text."""
    system = langfuse_client.get_prompt(secrets, "exam_validator_system", fallback=_VALIDATOR_SYSTEM)
    return call_claude(
        messages=[{"role": "user", "content": question_text}],
        system=system,
        api_key=api_key,
        secrets=secrets,
        max_tokens=4096,
        trace_name="exam_validate",
        session_id=session_id,
    )


def _call_judge(
    solution: str, answer_key_text: str, api_key: str, secrets: AppSecrets, session_id: str | None = None
) -> tuple[bool, str]:
    """Compare student solution to answer key. Fails closed on parse error."""
    prompt = (
        f"STUDENT SOLUTION:\n{solution}\n\n"
        f"ANSWER KEY:\n{answer_key_text}\n\n"
        "Does the student solution reach the same final answers as the answer key? "
        'Reply with JSON only: {"agrees": true|false, "notes": "brief"}'
    )
    system = langfuse_client.get_prompt(secrets, "exam_judge_system", fallback=_JUDGE_SYSTEM)
    raw = call_claude(
        messages=[{"role": "user", "content": prompt}],
        system=system,
        api_key=api_key,
        secrets=secrets,
        max_tokens=200,
        trace_name="exam_judge",
        session_id=session_id,
    )
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = json.loads(clean.strip())
        return bool(data.get("agrees", False)), str(data.get("notes", ""))
    except Exception:
        # Fail closed: unparseable response → mark as not validated
        return False, f"Judge response unparseable: {raw[:80]}"


def _build_question_text(exercise: dict) -> str:
    parts_lines = "\n".join(
        f"Part {p['part']} ({p['marks']} marks): {p['content']}"
        for p in exercise.get("parts", [])
    )
    return f"{exercise.get('content', '')}\n\n{parts_lines}"


def _build_answer_key_text(ak_exercise: dict) -> str:
    return "\n".join(
        f"Part {p['part']}: {p['answer']}"
        for p in ak_exercise.get("parts", [])
    )


def _exam_content_as_text(exam_content: ExamContent) -> str:
    lines: list[str] = []
    for ex in exam_content.exercises:
        lines.append(f"Exercise {ex.id} ({ex.topic}): {ex.content}")
        for part in ex.parts:
            lines.append(f"Part {part.part}: {part.content}")
    return "\n".join(lines)


def _call_regenerate(
    topic: str,
    total_marks: float,
    exercise_id: int,
    original_parts: list[dict],
    api_key: str,
    secrets: AppSecrets,
    session_id: str | None = None,
) -> tuple[dict, dict] | None:
    """Regenerate a single exercise preserving topic, total marks, and part breakdown."""
    parts_schema = ", ".join(
        f'part "{p["part"]}" = {p["marks"]} marks'
        for p in original_parts
    )
    prompt = (
        f"Generate a new Lebanese GS Grade 12 Math exercise on '{topic}', "
        f"worth exactly {total_marks} marks total.\n"
        f"Use exactly these part labels and mark allocations: {parts_schema}.\n"
        "Output ONLY a valid JSON object matching this structure:\n"
        f'{{"exercise": {{"id": {exercise_id}, "topic": "{topic}", '
        f'"total_marks": {total_marks}, "content": "...", '
        f'"parts": [{{"part": "...", "marks": ..., "content": "..."}}]}}, '
        f'"answer_key": {{"id": {exercise_id}, '
        f'"parts": [{{"part": "...", "marks": ..., "answer": "...", "partial_credit": ""}}]}}}}'
    )
    try:
        system = langfuse_client.get_prompt(secrets, "exam_regenerate_system", fallback=_REGENERATE_SYSTEM)
        raw = call_claude(
            messages=[{"role": "user", "content": prompt}],
            system=system,
            api_key=api_key,
            secrets=secrets,
            max_tokens=4096,
            trace_name="exam_regenerate",
            session_id=session_id,
        )
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = json.loads(clean.strip())
        return data["exercise"], data["answer_key"]
    except Exception:
        return None


# ── Async validation pipeline ─────────────────────────────────────────────────

async def _validate_exercise(
    exercise: dict, ak_exercise: dict, api_key: str, secrets: AppSecrets, session_id: str | None = None
) -> tuple[bool, str]:
    question_text = _build_question_text(exercise)
    answer_key_text = _build_answer_key_text(ak_exercise)
    solution = await asyncio.to_thread(_call_validator, question_text, api_key, secrets, session_id)
    agrees, notes = await asyncio.to_thread(_call_judge, solution, answer_key_text, api_key, secrets, session_id)
    return agrees, notes


async def _validate_exam_background(
    session_id: UUID,
    exam_content_dict: dict,
    answer_key_dict: dict,
    secrets: AppSecrets,
) -> None:
    exercises = exam_content_dict.get("exercises", [])
    ak_by_id = {ex["id"]: ex for ex in answer_key_dict.get("exercises", [])}

    async def _validate_one(exercise: dict) -> tuple[bool, str, dict | None, dict | None]:
        """Returns (is_valid, notes, replacement_exercise_or_None, replacement_ak_or_None)."""
        ak_ex = ak_by_id.get(exercise["id"], {})
        try:
            agrees, notes = await _validate_exercise(
                exercise, ak_ex, secrets.anthropic_api_key, secrets, str(session_id)
            )
        except Exception as exc:
            return False, f"Validation error: {str(exc)[:120]}", None, None

        if agrees:
            return True, notes, None, None

        # First attempt failed — regenerate once and revalidate
        regen = await asyncio.to_thread(
            _call_regenerate,
            exercise.get("topic", ""),
            float(exercise.get("total_marks", 5)),
            int(exercise.get("id", 1)),
            exercise.get("parts", []),
            secrets.anthropic_api_key,
            secrets,
            str(session_id),
        )
        if regen is None:
            return False, f"Validation failed; regeneration error. Initial: {notes}", None, None

        new_ex, new_ak_ex = regen
        try:
            agrees2, notes2 = await _validate_exercise(
                new_ex, new_ak_ex, secrets.anthropic_api_key, secrets, str(session_id)
            )
        except Exception as exc:
            return False, f"Retry validation error: {str(exc)[:120]}", None, None

        if agrees2:
            return True, f"Validated on retry. {notes2}", new_ex, new_ak_ex
        return False, f"Failed after retry. Initial: {notes}. Retry: {notes2}", None, None

    results = await asyncio.gather(*[_validate_one(ex) for ex in exercises])

    maker = _get_bg_maker(secrets.db_url)
    async with maker() as db_session:
        row = await exam_repo.get_session(db_session, session_id)
        if row is None:
            return

        current_exercises = (row.exam_content or {}).get("exercises", exercises)
        ak_exercises = list((row.answer_key or {}).get("exercises", []))
        ak_index = {ex["id"]: i for i, ex in enumerate(ak_exercises)}

        updated_exercises = []
        for ex, (is_valid, notes, new_ex, new_ak_ex) in zip(current_exercises, results):
            if new_ex is not None and row.status == SessionStatus.in_progress:
                # Safe to swap — student hasn't submitted yet
                updated_exercises.append({**new_ex, "is_validated": is_valid, "validation_notes": notes})
                if ex["id"] in ak_index:
                    ak_exercises[ak_index[ex["id"]]] = new_ak_ex
            else:
                # Submitted/graded or no replacement — annotate only, never change content
                updated_exercises.append({**ex, "is_validated": is_valid, "validation_notes": notes})

        row.exam_content = {**dict(row.exam_content or {}), "exercises": updated_exercises}
        if row.status == SessionStatus.in_progress:
            row.answer_key = {**dict(row.answer_key or {}), "exercises": ak_exercises}

        await db_session.commit()


# ── Public service functions ──────────────────────────────────────────────────

async def generate_exam(
    user_id: UUID,
    secrets: AppSecrets,
    db_session: AsyncSession,
    redis: Redis,
    session_type: SessionType = SessionType.mock_generated,
    generation_prompt: str | None = None,
) -> AsyncGenerator[str, None]:
    if generation_prompt:
        verdict = await guardrails_service.classify_input(generation_prompt)
        if verdict.category in (GuardrailCategory.prompt_injection, GuardrailCategory.harmful_content):
            await guardrails_service.log_event(
                db_session,
                user_id=user_id,
                conversation_id=None,
                source=GuardrailSource.exam_generation,
                direction=GuardrailDirection.input,
                category=verdict.category,
                level=GuardrailLevel.blocked,
                score=verdict.score,
                reason=verdict.reason,
                text=generation_prompt,
            )
            await db_session.commit()
            yield f"data: {json.dumps({'event': 'error', 'message': 'Your exam brief could not be processed.'})}\n\n"
            return

    await exam_repo.archive_active_sessions(db_session, user_id)

    conversation = await message_repo.create_conversation(db_session, user_id)

    placeholder_session = await exam_repo.create_session(
        session=db_session,
        user_id=user_id,
        conversation_id=conversation.id,
        session_type=session_type,
        exam_content={},
        answer_key={},
    )
    await db_session.commit()

    yield f"data: {json.dumps({'event': 'session_created', 'session_id': str(placeholder_session.id)})}\n\n"

    system = _build_generation_system_prompt()
    messages = [{"role": "user", "content": _build_generation_user_message(generation_prompt)}]

    try:
        raw = await asyncio.to_thread(
            call_claude, messages, system=system, api_key=secrets.anthropic_api_key, secrets=secrets,
            max_tokens=16000, trace_name="exam_generate", user_id=str(user_id),
            session_id=str(placeholder_session.id),
        )
        parsed = parse_generation_response(raw)
        exam_content = ExamContent.model_validate(parsed["exam"])
        answer_key = AnswerKey.model_validate(parsed["answer_key"])
        _validate_generated_payload(exam_content, answer_key)
    except Exception as exc:
        await db_session.delete(placeholder_session)
        await db_session.commit()
        yield f"data: {json.dumps({'event': 'error', 'message': str(exc) or 'AI service error'})}\n\n"
        return

    if not exam_content.exercises:
        await db_session.delete(placeholder_session)
        await db_session.commit()
        yield f"data: {json.dumps({'event': 'error', 'message': 'Model returned an empty exam. Please try again.'})}\n\n"
        return

    output_text = _exam_content_as_text(exam_content)
    output_verdict = await guardrails_service.classify_output(output_text)
    if output_verdict.flagged:
        await guardrails_service.log_event(
            db_session,
            user_id=user_id,
            conversation_id=conversation.id,
            source=GuardrailSource.exam_generation,
            direction=GuardrailDirection.output,
            category=None,
            level=GuardrailLevel.blocked,
            score=output_verdict.score,
            reason=output_verdict.reason,
            text=output_text,
        )
        await db_session.delete(placeholder_session)
        await db_session.commit()
        yield f"data: {json.dumps({'event': 'error', 'message': 'Generated exam failed a safety check. Please try again.'})}\n\n"
        return

    placeholder_session.exam_content = exam_content.model_dump()
    placeholder_session.answer_key = answer_key.model_dump()
    await db_session.commit()

    await set_session(redis, str(placeholder_session.id), {"answer_key": answer_key.model_dump()})

    yield f"data: {json.dumps({'event': 'exam_complete', 'exam_content': exam_content.model_dump()})}\n\n"

    yield "data: [DONE]\n\n"


async def list_sessions(
    user_id: UUID,
    db_session: AsyncSession,
) -> list[ExamSession]:
    rows = await exam_repo.list_sessions(db_session, user_id)
    return [_orm_to_domain(row) for row in rows if row.exam_content]


async def get_active_session(
    user_id: UUID,
    db_session: AsyncSession,
) -> ExamSession:
    row = await exam_repo.get_active_session(db_session, user_id)
    if row is None:
        raise ExamNotFound("No active exam session found.")
    return _orm_to_domain(row)


async def get_session_by_id(
    session_id: UUID,
    user_id: UUID,
    db_session: AsyncSession,
) -> ExamSession:
    row = await exam_repo.get_session(db_session, session_id)
    if row is None or row.user_id != user_id:
        raise ExamNotFound(f"Exam session {session_id} not found.")
    return _orm_to_domain(row)


def _orm_to_domain(row) -> ExamSession:
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return ExamSession(
        id=row.id,
        user_id=row.user_id,
        session_type=row.session_type,
        status=row.status,
        exam_content=ExamContent.model_validate(row.exam_content or {}),
        created_at=created,
    )


async def extract_answers(
    session_id: UUID,
    user_id: UUID,
    file_bytes: bytes,
    mime_type: str,
    db_session: AsyncSession,
    secrets: AppSecrets,
) -> dict:
    """Extract handwritten answers from an image or PDF using Claude Vision."""
    import logging
    import re
    logging.getLogger(__name__).info("extract_answers: session=%s mime=%r size=%d", session_id, mime_type, len(file_bytes))

    row = await exam_repo.get_session(db_session, session_id)
    if row is None or row.user_id != user_id:
        raise ExamNotFound(f"Exam session {session_id} not found.")

    prompt = build_extraction_prompt(row.exam_content or {})

    raw = await asyncio.to_thread(
        call_claude_vision,
        file_bytes,
        mime_type,
        prompt,
        secrets.anthropic_api_key,
        secrets,
        max_tokens=8192,
        prefill="{",
        trace_name="exam_extract_answers",
        user_id=str(user_id),
        session_id=str(session_id),
    )

    logging.getLogger(__name__).info("extract_answers raw response (first 500 chars): %r", raw[:500])

    # Prefill guarantees response starts with "{"; parse directly.
    # Strip any trailing text after the closing brace of the top-level object.
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Find the outermost balanced { ... } in case Claude added trailing text
        depth = 0
        end = -1
        for i, ch in enumerate(raw):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > 0:
            try:
                data = json.loads(raw[:end])
            except json.JSONDecodeError:
                raise ExtractionFailed(f"Parse failed. Raw (first 300): {raw[:300]!r}")
        else:
            raise ExtractionFailed(f"No JSON object found. Raw (first 300): {raw[:300]!r}")

    if "answers" not in data:
        raise ExtractionFailed("Extraction response is missing the 'answers' field.")

    return data
