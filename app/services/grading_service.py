"""Dual-evaluator grading service.

Two independent Claude evaluators (strict vs. lenient) grade the same
submission in parallel. Per-question score differences are flagged as
discrepancies. Results are persisted permanently (FR-025).
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import SessionStatus
from app.domain.exceptions import (
    AIServiceUnavailable,
    ExamNotFound,
    InvalidAnswerSubmission,
    SessionExpired,
)
from app.domain.models import EvaluationResult, EvaluatorScore
from app.infra.llm.claude import call_claude
from app.infra.vault import AppSecrets
from app.repositories import exam_repo

_PERSONA_INSTRUCTIONS = {
    "strict": (
        "You are a STRICT examiner for the official Lebanese GS Grade 12 Math "
        "baccalaureate. When in doubt, DEDUCT marks. Require complete, rigorous "
        "justification; penalise missing steps, unstated theorems, and notation errors."
    ),
    "lenient": (
        "You are a LENIENT examiner for the official Lebanese GS Grade 12 Math "
        "baccalaureate. When in doubt, AWARD marks. Reward correct method and "
        "understanding even when the final answer or some steps are imperfect."
    ),
}


def _build_evaluator_prompt(
    persona: str,
    exam_content: dict,
    answers: list[dict],
    answer_key: dict,
) -> str:
    return f"""{_PERSONA_INSTRUCTIONS[persona]}

You will be given the exam, the official answer key, and the student's answers.
Grade every sub-question. Allocate marks per the exam's per-part mark values.

EXAM:
{json.dumps(exam_content, indent=2)}

OFFICIAL ANSWER KEY:
{json.dumps(answer_key, indent=2)}

STUDENT ANSWERS:
{json.dumps(answers, indent=2)}

Return ONLY a valid JSON object (no prose, no markdown fences) with EXACTLY these keys:
{{
  "scores": {{"Q1_1": 2.0, "Q1_2": 1.5}},   // key format "Q{{exercise_id}}_{{part}}", value = marks awarded
  "total": 18.5,                              // sum of all awarded marks
  "feedback": "concise overall feedback",
  "missing_keywords": ["theorem name", "..."] // key concepts the student omitted
}}"""


def _parse_evaluator_json(raw: str) -> dict:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[-1]
        if clean.endswith("```"):
            clean = clean[: clean.rfind("```")]
    return json.loads(clean)


def _call_evaluator(
    persona: str,
    exam_content: dict,
    answers: list[dict],
    answer_key: dict,
    api_key: str,
) -> EvaluatorScore:
    """Synchronous single-evaluator call — run via asyncio.to_thread()."""
    system = _build_evaluator_prompt(persona, exam_content, answers, answer_key)
    messages = [{"role": "user", "content": "Grade this submission and return the JSON object."}]
    raw = call_claude(messages, system=system, api_key=api_key, max_tokens=2048)
    try:
        parsed = _parse_evaluator_json(raw)
        return EvaluatorScore(
            scores={k: float(v) for k, v in parsed.get("scores", {}).items()},
            total=float(parsed.get("total", 0.0)),
            feedback=str(parsed.get("feedback", "")),
            missing_keywords=list(parsed.get("missing_keywords", [])),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise AIServiceUnavailable(f"Evaluator returned malformed JSON: {exc}") from exc


def _detect_discrepancy(
    ev1: EvaluatorScore,
    ev2: EvaluatorScore,
) -> tuple[bool, str | None]:
    """Flag any sub-question where the two evaluators disagree.

    Compares the UNION of both score dicts' keys — a key present in only one
    evaluator counts as a discrepancy.
    """
    keys = set(ev1.scores) | set(ev2.scores)
    differing: list[str] = []
    for key in sorted(keys):
        s1 = ev1.scores.get(key)
        s2 = ev2.scores.get(key)
        if s1 != s2:
            differing.append(f"{key}: strict={s1} lenient={s2}")
    if not differing:
        return False, None
    return True, "; ".join(differing)


def _ensure_aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


async def validate_submission(
    session_id: UUID,
    user_id: UUID,
    answers: list[dict],
    db_session: AsyncSession,
) -> tuple[dict, dict]:
    """Pre-flight checks — MUST run in the awaited router body, NOT inside the
    streaming generator.

    Starlette sends the HTTP 200 + headers before iterating a StreamingResponse,
    so any exception raised inside the generator fires after the response has
    started and can no longer be mapped to a 4xx status (Principle IV). Raising
    here, while the router awaits, lets the domain→HTTP handlers map correctly.

    Returns (exam_content, answer_key) — both read from the authoritative DB row.
    """
    row = await exam_repo.get_session(db_session, session_id)
    if row is None or row.user_id != user_id:
        raise ExamNotFound(f"Exam session {session_id} not found.")
    if row.status != SessionStatus.in_progress:
        raise InvalidAnswerSubmission(
            f"Exam session {session_id} is already {row.status.value}."
        )
    if _ensure_aware(row.expires_at) < datetime.now(timezone.utc):
        raise SessionExpired(f"Exam session {session_id} has expired.")

    exam_content: dict = row.exam_content or {}
    valid_ids = {ex["id"] for ex in exam_content.get("exercises", [])}
    submitted_ids = {a["exercise_id"] for a in answers}
    if not submitted_ids or not submitted_ids.issubset(valid_ids):
        raise InvalidAnswerSubmission(
            f"Submitted exercise IDs {sorted(submitted_ids)} do not match exam {sorted(valid_ids)}."
        )

    # Authoritative answer key lives on the session row (also mirrored to Redis with a TTL).
    answer_key: dict = row.answer_key or {}
    return exam_content, answer_key


async def submit_answers(
    session_id: UUID,
    user_id: UUID,
    answers: list[dict],
    exam_content: dict,
    answer_key: dict,
    db_session: AsyncSession,
    secrets: AppSecrets,
) -> AsyncGenerator[str, None]:
    """Stream the dual evaluation. Pre-flight validation is done by the caller via
    validate_submission() BEFORE the StreamingResponse is constructed."""
    yield f"data: {json.dumps({'event': 'evaluating'})}\n\n"

    try:
        ev1, ev2 = await asyncio.gather(
            asyncio.to_thread(
                _call_evaluator, "strict", exam_content, answers, answer_key, secrets.anthropic_api_key
            ),
            asyncio.to_thread(
                _call_evaluator, "lenient", exam_content, answers, answer_key, secrets.anthropic_api_key
            ),
        )
    except AIServiceUnavailable as exc:
        # The 200 + headers are already on the wire — surface the failure as an
        # SSE error event rather than raising (which can no longer set a status).
        yield f"data: {json.dumps({'event': 'error', 'message': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"
        return

    yield f"data: {json.dumps({'event': 'evaluator_1_complete', 'evaluator': ev1.model_dump()})}\n\n"
    yield f"data: {json.dumps({'event': 'evaluator_2_complete', 'evaluator': ev2.model_dump()})}\n\n"

    flagged, details = _detect_discrepancy(ev1, ev2)

    await exam_repo.save_result(
        session=db_session,
        session_id=session_id,
        user_id=user_id,
        student_answers={"answers": answers},
        evaluator_1=ev1.model_dump(),
        evaluator_2=ev2.model_dump(),
        total_score_1=ev1.total,
        total_score_2=ev2.total,
        discrepancy_flagged=flagged,
        discrepancy_details=details,
    )
    await exam_repo.update_session_status(db_session, session_id, SessionStatus.graded)
    await db_session.commit()

    result = EvaluationResult(
        session_id=session_id,
        evaluator_1=ev1,
        evaluator_2=ev2,
        total_score_1=ev1.total,
        total_score_2=ev2.total,
        discrepancy_flagged=flagged,
        discrepancy_details=details,
    )
    yield f"data: {json.dumps({'event': 'grading_complete', 'result': result.model_dump(mode='json')})}\n\n"
    yield "data: [DONE]\n\n"


async def get_results(
    session_id: UUID,
    user_id: UUID,
    db_session: AsyncSession,
) -> EvaluationResult:
    row = await exam_repo.get_result(db_session, session_id)
    if row is None or row.user_id != user_id:
        raise ExamNotFound(f"Results for session {session_id} not available.")

    ev1 = EvaluatorScore.model_validate(row.evaluator_1)
    ev2 = EvaluatorScore.model_validate(row.evaluator_2)
    # discrepancy_details is not persisted — recompute from stored evaluator scores.
    _, details = _detect_discrepancy(ev1, ev2)
    return EvaluationResult(
        session_id=row.session_id,
        evaluator_1=ev1,
        evaluator_2=ev2,
        total_score_1=row.total_score_1,
        total_score_2=row.total_score_2,
        discrepancy_flagged=row.discrepancy_flagged,
        discrepancy_details=details,
    )
