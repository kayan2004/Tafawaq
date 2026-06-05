"""Chunk repository — asyncpg + pgvector.

Uses asyncpg directly (not SQLAlchemy) because the pgvector <=> operator
requires raw SQL that SQLAlchemy cannot express without custom type handling.
"""
from __future__ import annotations

import asyncpg
import pgvector.asyncpg


async def cosine_similarity_search(
    conn: asyncpg.Connection,
    embedding: list[float],
    topic: str | None,
    question_type: str | None,
    year_from: int | None,
    year_to: int | None,
    limit: int = 10,
) -> list[asyncpg.Record]:
    await pgvector.asyncpg.register_vector(conn)
    return await conn.fetch(
        """
        SELECT
            id,
            year,
            session,
            exercise_id,
            topic,
            subtopic,
            question_type,
            marks,
            content,
            1 - (embedding <=> $1::vector) AS similarity
        FROM chunks
        WHERE source_type = 'past_exam'
          AND ($2::text IS NULL OR topic ILIKE $2)
          AND ($3::text IS NULL OR question_type::text = $3)
          AND ($4::int  IS NULL OR year >= $4)
          AND ($5::int  IS NULL OR year <= $5)
        ORDER BY embedding <=> $1::vector
        LIMIT $6
        """,
        embedding,
        topic,
        question_type,
        year_from,
        year_to,
        limit,
    )


async def get_answer_key(
    conn: asyncpg.Connection,
    year: int,
    session: int,
    exercise_id: int,
) -> str | None:
    await pgvector.asyncpg.register_vector(conn)
    row = await conn.fetchrow(
        """
        SELECT content
        FROM chunks
        WHERE source_type = 'answer_key'
          AND year = $1
          AND session = $2
          AND exercise_id = $3
        LIMIT 1
        """,
        year,
        session,
        exercise_id,
    )
    return row["content"] if row else None
