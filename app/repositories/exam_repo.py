"""Exam session and result CRUD — SQLAlchemy AsyncSession."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import SessionStatus, SessionType
from app.repositories.orm import ExamResultORM, ExamSessionORM

_FAR_FUTURE = datetime(2099, 12, 31, tzinfo=timezone.utc)


async def create_session(
    session: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
    session_type: SessionType,
    exam_content: dict,
    answer_key: dict,
) -> ExamSessionORM:
    row = ExamSessionORM(
        user_id=user_id,
        conversation_id=conversation_id,
        session_type=session_type,
        exam_content=exam_content,
        answer_key=answer_key,
        status=SessionStatus.in_progress,
        expires_at=_FAR_FUTURE,
    )
    session.add(row)
    await session.flush()   # resolve FK before caller commits
    await session.refresh(row)
    return row


async def get_session(
    session: AsyncSession,
    session_id: UUID,
) -> ExamSessionORM | None:
    result = await session.execute(
        select(ExamSessionORM).where(ExamSessionORM.id == session_id)
    )
    return result.scalar_one_or_none()


async def get_active_session(
    session: AsyncSession,
    user_id: UUID,
) -> ExamSessionORM | None:
    result = await session.execute(
        select(ExamSessionORM)
        .where(
            ExamSessionORM.user_id == user_id,
            ExamSessionORM.status == SessionStatus.in_progress,
        )
        .order_by(ExamSessionORM.created_at.desc())
    )
    return result.scalars().first()


async def archive_active_sessions(
    session: AsyncSession,
    user_id: UUID,
) -> None:
    """Set all in_progress sessions for this user to submitted."""
    await session.execute(
        update(ExamSessionORM)
        .where(
            ExamSessionORM.user_id == user_id,
            ExamSessionORM.status == SessionStatus.in_progress,
        )
        .values(status=SessionStatus.submitted)
    )


async def update_session_status(
    session: AsyncSession,
    session_id: UUID,
    status: SessionStatus,
) -> None:
    row = await get_session(session, session_id)
    if row is not None:
        row.status = status
        await session.flush()


async def save_result(
    session: AsyncSession,
    session_id: UUID,
    user_id: UUID,
    student_answers: dict,
    evaluator_1: dict,
    evaluator_2: dict,
    total_score_1: float,
    total_score_2: float,
    discrepancy_flagged: bool,
    discrepancy_details: str | None = None,
) -> ExamResultORM:
    row = ExamResultORM(
        session_id=session_id,
        user_id=user_id,
        student_answers=student_answers,
        evaluator_1=evaluator_1,
        evaluator_2=evaluator_2,
        total_score_1=total_score_1,
        total_score_2=total_score_2,
        discrepancy_flagged=discrepancy_flagged,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def list_sessions(
    session: AsyncSession,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[ExamSessionORM]:
    result = await session.execute(
        select(ExamSessionORM)
        .where(ExamSessionORM.user_id == user_id)
        .order_by(ExamSessionORM.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars())


async def get_result(
    session: AsyncSession,
    session_id: UUID,
) -> ExamResultORM | None:
    result = await session.execute(
        select(ExamResultORM).where(ExamResultORM.session_id == session_id)
    )
    return result.scalar_one_or_none()


async def get_result_with_session(
    session: AsyncSession,
    session_id: UUID,
) -> tuple[ExamResultORM, ExamSessionORM] | None:
    """Returns (result_row, session_row) or None if the result does not exist."""
    result_row = await get_result(session, session_id)
    if result_row is None:
        return None
    session_row = await get_session(session, result_row.session_id)
    if session_row is None:
        return None
    return result_row, session_row


async def get_history(
    session: AsyncSession,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[ExamResultORM]]:
    count_result = await session.execute(
        select(func.count()).select_from(ExamResultORM).where(ExamResultORM.user_id == user_id)
    )
    total = count_result.scalar_one()

    rows_result = await session.execute(
        select(ExamResultORM)
        .where(ExamResultORM.user_id == user_id)
        .order_by(ExamResultORM.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = list(rows_result.scalars())
    return total, rows
