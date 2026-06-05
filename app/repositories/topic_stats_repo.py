"""Topic stats repository — SQLAlchemy AsyncSession."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import TopicNotFound
from app.repositories.orm import ChunkORM, TopicStatsORM


async def get_all_topic_stats(session: AsyncSession) -> list[TopicStatsORM]:
    result = await session.execute(
        select(TopicStatsORM).order_by(TopicStatsORM.appearances.desc())
    )
    return list(result.scalars().all())


async def get_questions_by_topic(
    session: AsyncSession,
    topic: str,
    year_from: int | None = None,
    year_to: int | None = None,
    question_type: str | None = None,
    limit: int = 50,
) -> list[ChunkORM]:
    stat_row = await session.execute(
        select(TopicStatsORM).where(TopicStatsORM.topic == topic)
    )
    if stat_row.scalars().first() is None:
        raise TopicNotFound(f"Topic '{topic}' not found in the exam archive.")

    stmt = (
        select(ChunkORM)
        .where(
            ChunkORM.source_type == "past_exam",
            ChunkORM.topic == topic,
        )
        .order_by(ChunkORM.year.desc())
        .limit(limit)
    )
    if year_from is not None:
        stmt = stmt.where(ChunkORM.year >= year_from)
    if year_to is not None:
        stmt = stmt.where(ChunkORM.year <= year_to)
    if question_type is not None:
        stmt = stmt.where(ChunkORM.question_type == question_type)

    result = await session.execute(stmt)
    return list(result.scalars().all())
