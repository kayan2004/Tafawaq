"""Retrieval service — semantic search over past exam chunks."""
from __future__ import annotations

import asyncio

import asyncpg

from app.domain.models import PastQuestion
from app.infra.embeddings.voyage import embed_text
from app.infra.vault import AppSecrets
from app.repositories import chunk_repo


async def retrieve_past_questions(
    query: str,
    topic: str | None,
    question_type: str | None,
    year_from: int | None,
    year_to: int | None,
    limit: int,
    secrets: AppSecrets,
    conn: asyncpg.Connection,
) -> list[PastQuestion]:
    # embed_text is sync (voyageai SDK) — run in thread to avoid blocking event loop
    embedding = await asyncio.to_thread(embed_text, query, secrets.voyage_api_key)

    rows = await chunk_repo.cosine_similarity_search(
        conn, embedding, topic, question_type, year_from, year_to, limit,
        source_types=["past_exam"],
    )

    questions: list[PastQuestion] = []
    for row in rows:
        answer = await chunk_repo.get_answer_key(
            conn, row["year"], row["session"], row["exercise_id"]
        )
        questions.append(
            PastQuestion(
                chunk_id=row["id"],
                year=row["year"],
                session=row["session"],
                exercise_id=row["exercise_id"],
                topic=row["topic"],
                subtopic=row["subtopic"],
                question_type=row["question_type"],
                marks=row["marks"],
                content=row["content"],
                answer=answer,
                similarity_score=float(row["similarity"]),
            )
        )
    return questions
