"""Topic analytics service."""
from __future__ import annotations

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import PastQuestion, TopicStat
from app.repositories import chunk_repo, topic_stats_repo


def _frequency_tier(appearances: int) -> str:
    # high  ≥ 14 ≈ 7+ of last 10 exam years at 2 sessions/year
    # medium 7–13
    # low   ≤ 6
    if appearances >= 14:
        return "high"
    if appearances >= 7:
        return "medium"
    return "low"


async def get_all_topic_stats(session: AsyncSession) -> list[TopicStat]:
    rows = await topic_stats_repo.get_all_topic_stats(session)
    return [
        TopicStat(
            topic=row.topic,
            appearances=row.appearances,
            last_seen_year=row.last_seen_year,
            last_seen_session=row.last_seen_session,
            frequency_tier=_frequency_tier(row.appearances),
        )
        for row in rows
    ]


async def get_questions_by_topic(
    session: AsyncSession,
    conn: asyncpg.Connection,
    topic: str,
    year_from: int | None,
    year_to: int | None,
    question_type: str | None,
    limit: int,
) -> list[PastQuestion]:
    # Raises TopicNotFound if topic absent — propagates to 404 handler
    orm_rows = await topic_stats_repo.get_questions_by_topic(
        session, topic, year_from, year_to, question_type, limit
    )

    questions: list[PastQuestion] = []
    for row in orm_rows:
        answer = await chunk_repo.get_answer_key(
            conn, row.year, row.session, row.exercise_id
        )
        questions.append(
            PastQuestion(
                chunk_id=row.id,
                year=row.year,
                session=row.session,
                exercise_id=row.exercise_id,
                topic=row.topic,
                subtopic=row.subtopic,
                question_type=row.question_type,
                marks=row.marks,
                content=row.content,
                answer=answer,
            )
        )
    return questions
