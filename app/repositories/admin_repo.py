"""Admin panel repository — aggregate queries only. SQL only, no HTTP errors."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.orm import (
    ChunkORM,
    ExamResultORM,
    ExamSessionORM,
    MessageORM,
    TextbookPageORM,
    TopicStatsORM,
    UserDetailsORM,
    UserORM,
)


async def count_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(UserORM))
    return result.scalar_one()


async def count_onboarded_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(UserDetailsORM))
    return result.scalar_one()


async def count_exam_sessions(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(ExamSessionORM))
    return result.scalar_one()


async def count_exam_results(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(ExamResultORM))
    return result.scalar_one()


async def count_chunks_by_source_type(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(
        select(ChunkORM.source_type, func.count()).group_by(ChunkORM.source_type)
    )
    return {source_type: count for source_type, count in result.all()}


async def count_topics(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(TopicStatsORM))
    return result.scalar_one()


async def count_messages(session: AsyncSession, since: datetime | None = None) -> int:
    stmt = select(func.count()).select_from(MessageORM)
    if since is not None:
        stmt = stmt.where(MessageORM.created_at >= since)
    result = await session.execute(stmt)
    return result.scalar_one()


async def count_past_exam_chunks_by_year_session(
    session: AsyncSession,
) -> dict[tuple[int, int], int]:
    result = await session.execute(
        select(ChunkORM.year, ChunkORM.session, func.count())
        .where(ChunkORM.source_type == "past_exam")
        .group_by(ChunkORM.year, ChunkORM.session)
    )
    return {(year, sess): count for year, sess, count in result.all()}


async def list_textbook_chapter_meta(session: AsyncSession) -> list[dict]:
    """Group textbook_pages by chapter: page count + page range."""
    result = await session.execute(
        select(
            TextbookPageORM.chapter,
            func.count().label("page_count"),
            func.min(TextbookPageORM.page_number).label("min_page"),
            func.max(TextbookPageORM.page_number).label("max_page"),
        ).group_by(TextbookPageORM.chapter)
    )
    return [
        {"chapter": chapter, "page_count": page_count, "min_page": min_page, "max_page": max_page}
        for chapter, page_count, min_page, max_page in result.all()
    ]


async def list_users_with_aggregates(session: AsyncSession) -> list[dict]:
    """One row per user: profile + onboarding flag + exam aggregates."""
    onboarded_result = await session.execute(select(UserDetailsORM.user_id))
    onboarded_ids = {row[0] for row in onboarded_result.all()}

    agg_result = await session.execute(
        select(
            ExamResultORM.user_id,
            func.count().label("exam_count"),
            func.avg((ExamResultORM.total_score_1 + ExamResultORM.total_score_2) / 2).label("avg_score"),
        ).group_by(ExamResultORM.user_id)
    )
    agg_by_user = {row.user_id: (row.exam_count, row.avg_score) for row in agg_result.all()}

    users_result = await session.execute(select(UserORM).order_by(UserORM.created_at.desc()))
    rows = []
    for user in users_result.scalars():
        exam_count, avg_score = agg_by_user.get(user.id, (0, None))
        rows.append(
            {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "last_login": user.last_login,
                "onboarded": user.id in onboarded_ids,
                "exam_count": exam_count,
                "avg_score": float(avg_score) if avg_score is not None else None,
            }
        )
    return rows


async def deactivate_user(session: AsyncSession, user_id: UUID) -> bool:
    """Returns False if no user with this id exists, True once deactivated."""
    result = await session.execute(select(UserORM).where(UserORM.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return False
    user.is_active = False
    await session.commit()
    return True
