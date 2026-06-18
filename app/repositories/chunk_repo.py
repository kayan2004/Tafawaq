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
    source_types: list[str] | None = None,
) -> list[asyncpg.Record]:
    await pgvector.asyncpg.register_vector(conn)
    return await conn.fetch(
        """
        SELECT
            c.id,
            c.source_type,
            c.year,
            c.session,
            c.exercise_id,
            c.topic,
            c.question_type,
            c.marks,
            c.content,
            1 - (c.embedding <=> $1::vector) AS similarity
        FROM chunks c
        WHERE ($2::text[] IS NULL OR c.source_type = ANY($2::text[]))
          AND ($3::text IS NULL OR c.topic ILIKE $3)
          AND ($4::text IS NULL OR c.question_type::text = $4)
          AND ($5::int  IS NULL OR c.year >= $5)
          AND ($6::int  IS NULL OR c.year <= $6)
        ORDER BY c.embedding <=> $1::vector
        LIMIT $7
        """,
        embedding,
        source_types,
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
