"""Retrieval service — semantic search over past exam chunks and textbook sections."""
from __future__ import annotations

import asyncio

import asyncpg

from app.domain.models import PastQuestion, TextbookSection
from app.infra.embeddings.voyage import embed_text
from app.infra.vault import AppSecrets
from app.repositories import chunk_repo

_TEXTBOOK_SOURCE_TYPES = ["textbook_theory", "textbook_exercise", "textbook_self_evaluation"]


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


async def retrieve_textbook_sections(
    query: str,
    source_types: list[str] | None,
    limit: int,
    secrets: AppSecrets,
    conn: asyncpg.Connection,
) -> list[TextbookSection]:
    embedding = await asyncio.to_thread(embed_text, query, secrets.voyage_api_key)

    effective_source_types = source_types or _TEXTBOOK_SOURCE_TYPES
    rows = await chunk_repo.cosine_similarity_search(
        conn, embedding,
        topic=None,
        question_type=None,
        year_from=None,
        year_to=None,
        limit=limit,
        source_types=effective_source_types,
    )

    return [
        TextbookSection(
            chunk_id=row["id"],
            chapter=row["chapter"] or "",
            section=row["section"] or "",
            topic=row["topic"],
            subtopic=row["subtopic"],
            source_type=row["source_type"],
            page_start=row["page_start"],
            page_end=row["page_end"],
            content=row["content"],
            similarity=float(row["similarity"]),
        )
        for row in rows
    ]
