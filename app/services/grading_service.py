"""Dual-evaluator grading service.

Two independent Claude evaluators (strict vs. lenient) grade the same
submission in parallel via asyncio.gather. Results are persisted permanently.
"""
from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from minio import Minio

from app.domain.enums import SessionStatus
from app.domain.exceptions import ExamNotFound, InvalidAnswerSubmission
from app.domain.grading import CorrectionResult, EvaluatorResult
from app.infra.evaluator import call_evaluator, call_pdf_evaluator
from app.infra.minio_client import PAST_EXAMS_BUCKET, get_pdf_bytes
from app.infra.vault import AppSecrets
from app.repositories import exam_repo


def _fetch_pdf(minio_access_key: str, minio_secret_key: str, pdf_key: str) -> bytes:
    client = Minio("minio:9000", access_key=minio_access_key, secret_key=minio_secret_key, secure=False)
    return get_pdf_bytes(client, PAST_EXAMS_BUCKET, pdf_key)


def _discrepancy(ev1: EvaluatorResult, ev2: EvaluatorResult) -> tuple[bool, str | None]:
    delta = abs(ev1.grand_total - ev2.grand_total)
    if delta < 2.0:
        return False, None
    detail = (
        f"Evaluator 1: {ev1.grand_total:.1f}/{ev1.grand_max:.0f}, "
        f"Evaluator 2: {ev2.grand_total:.1f}/{ev2.grand_max:.0f} "
        f"(delta: {delta:.1f})"
    )
    return True, detail


async def grade(
    session_id: UUID,
    user_id: UUID,
    answers: list[dict],
    db_session: AsyncSession,
    secrets: AppSecrets,
) -> CorrectionResult:
    row = await exam_repo.get_session(db_session, session_id)
    if row is None or row.user_id != user_id:
        raise ExamNotFound(f"Exam session {session_id} not found.")
    if row.status != SessionStatus.in_progress:
        raise InvalidAnswerSubmission(
            f"Exam session {session_id} is already {row.status.value}."
        )

    exam_content: dict = row.exam_content or {}
    answer_key: dict = row.answer_key or {}

    valid_ids = {ex["id"] for ex in exam_content.get("exercises", [])}
    submitted_ids = {a["exercise_id"] for a in answers}
    if not submitted_ids or not submitted_ids.issubset(valid_ids):
        raise InvalidAnswerSubmission(
            f"Submitted exercise IDs {sorted(submitted_ids)} do not match exam {sorted(valid_ids)}."
        )

    pdf_key = answer_key.get("pdf_key")
    if pdf_key:
        pdf_bytes = await asyncio.to_thread(
            _fetch_pdf, secrets.minio_access_key, secrets.minio_secret_key, pdf_key
        )
        ev1, ev2 = await asyncio.gather(
            asyncio.to_thread(
                call_pdf_evaluator, "strict", exam_content, pdf_bytes,
                answers, secrets.anthropic_api_key,
            ),
            asyncio.to_thread(
                call_pdf_evaluator, "lenient", exam_content, pdf_bytes,
                answers, secrets.anthropic_api_key,
            ),
        )
    else:
        ev1, ev2 = await asyncio.gather(
            asyncio.to_thread(
                call_evaluator, "strict", exam_content, answer_key,
                answers, secrets.anthropic_api_key,
            ),
            asyncio.to_thread(
                call_evaluator, "lenient", exam_content, answer_key,
                answers, secrets.anthropic_api_key,
            ),
        )

    flagged, details = _discrepancy(ev1, ev2)

    await exam_repo.save_result(
        session=db_session,
        session_id=session_id,
        user_id=user_id,
        student_answers={"answers": answers},
        evaluator_1=ev1.model_dump(mode="json"),
        evaluator_2=ev2.model_dump(mode="json"),
        total_score_1=ev1.grand_total,
        total_score_2=ev2.grand_total,
        discrepancy_flagged=flagged,
        discrepancy_details=details,
    )
    await exam_repo.update_session_status(db_session, session_id, SessionStatus.graded)
    await db_session.commit()

    return CorrectionResult(
        session_id=session_id,
        evaluator_1=ev1,
        evaluator_2=ev2,
        discrepancy_flagged=flagged,
        discrepancy_details=details,
        average_total=round((ev1.grand_total + ev2.grand_total) / 2, 2),
        exam_content=exam_content,
        student_answers=answers,
    )


async def get_results(
    session_id: UUID,
    user_id: UUID,
    db_session: AsyncSession,
) -> CorrectionResult:
    pair = await exam_repo.get_result_with_session(db_session, session_id)
    if pair is None or pair[0].user_id != user_id:
        raise ExamNotFound(f"Results for session {session_id} not available.")

    row, session_row = pair
    ev1 = EvaluatorResult.model_validate(row.evaluator_1)
    ev2 = EvaluatorResult.model_validate(row.evaluator_2)
    flagged, details = _discrepancy(ev1, ev2)
    # student_answers is stored as {"answers": [...]} — unwrap the list
    student_answers: list[dict] = (row.student_answers or {}).get("answers", [])
    return CorrectionResult(
        session_id=row.session_id,
        evaluator_1=ev1,
        evaluator_2=ev2,
        discrepancy_flagged=row.discrepancy_flagged,
        discrepancy_details=details,
        average_total=round((row.total_score_1 + row.total_score_2) / 2, 2),
        exam_content=session_row.exam_content or {},
        student_answers=student_answers,
    )
