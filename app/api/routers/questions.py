"""POST /questions/retrieve — semantic search over past exam chunks."""
from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import get_db_conn, get_secrets
from app.infra.auth import current_active_user
from app.infra.vault import AppSecrets
from app.repositories.orm import UserORM
from app.services import retrieval_service

router = APIRouter(prefix="/questions", tags=["questions"])


class QuestionRetrieveRequest(BaseModel):
    query: str
    topic: str | None = None
    question_type: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    limit: int = Field(default=10, ge=1, le=50)


@router.post("/retrieve")
async def retrieve_questions(
    body: QuestionRetrieveRequest,
    _user: UserORM = Depends(current_active_user),
    secrets: AppSecrets = Depends(get_secrets),
    conn: asyncpg.Connection = Depends(get_db_conn),
):
    results = await retrieval_service.retrieve_past_questions(
        query=body.query,
        topic=body.topic,
        question_type=body.question_type,
        year_from=body.year_from,
        year_to=body.year_to,
        limit=body.limit,
        secrets=secrets,
        conn=conn,
    )
    if not results:
        return {
            "total_returned": 0,
            "questions": [],
            "suggestion": (
                "No past questions found for this query. "
                "Try broadening the year range or topic."
            ),
        }
    return {
        "total_returned": len(results),
        "questions": [q.model_dump() for q in results],
    }
