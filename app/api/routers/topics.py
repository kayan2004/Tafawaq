"""GET /topics/stats and GET /topics/{topic}/questions — topic analytics."""
from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session, get_db_conn
from app.infra.auth import current_active_user
from app.repositories.orm import UserORM
from app.services import topic_service

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/stats")
async def get_topic_stats(
    _user: UserORM = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    stats = await topic_service.get_all_topic_stats(session)
    return {"topics": [t.model_dump() for t in stats]}


@router.get("/{topic}/questions")
async def get_questions_by_topic(
    topic: str,
    year_from: int | None = Query(default=None),
    year_to: int | None = Query(default=None),
    question_type: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    _user: UserORM = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    conn: asyncpg.Connection = Depends(get_db_conn),
):
    questions = await topic_service.get_questions_by_topic(
        session=session,
        conn=conn,
        topic=topic,
        year_from=year_from,
        year_to=year_to,
        question_type=question_type,
        limit=limit,
    )
    return {
        "topic": topic,
        "total_returned": len(questions),
        "questions": [q.model_dump() for q in questions],
    }
