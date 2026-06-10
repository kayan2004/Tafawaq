"""POST /grade, GET /exams/history, GET /exams/{session_id}/results."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session, get_secrets
from app.infra.auth import current_active_user
from app.infra.vault import AppSecrets
from app.repositories import exam_repo
from app.repositories.orm import UserORM
from app.services import grading_service

# NOTE: registered BEFORE the exams router in main.py so GET /exams/history (literal)
# is not shadowed by the exams router's GET /exams/{session_id} (param) route.
router = APIRouter(tags=["grading"])


class AnswerPart(BaseModel):
    part: str
    answer: str
    submitted_at: str


class ExerciseAnswer(BaseModel):
    exercise_id: int
    parts: list[AnswerPart]


class GradeRequest(BaseModel):
    session_id: UUID
    answers: list[ExerciseAnswer]


@router.post("/grade")
async def submit_for_grading(
    body: GradeRequest,
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
    secrets: AppSecrets = Depends(get_secrets),
):
    answers = [a.model_dump(mode="json") for a in body.answers]
    result = await grading_service.grade(
        session_id=body.session_id,
        user_id=user.id,
        answers=answers,
        db_session=db_session,
        secrets=secrets,
    )
    return result.model_dump(mode="json")


@router.get("/exams/history")
async def get_history(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
):
    total, rows = await exam_repo.get_history(db_session, user.id, limit=limit, offset=offset)
    return {
        "total": total,
        "results": [
            {
                "session_id": str(r.session_id),
                "total_score_1": r.total_score_1,
                "total_score_2": r.total_score_2,
                "discrepancy_flagged": r.discrepancy_flagged,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@router.get("/exams/{session_id}/results")
async def get_results(
    session_id: UUID,
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
):
    result = await grading_service.get_results(session_id, user.id, db_session)
    return result.model_dump(mode="json")
