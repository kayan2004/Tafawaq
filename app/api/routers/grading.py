"""POST /exams/{id}/submit, GET /exams/{id}/results, GET /exams/history."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session, get_secrets
from app.infra.auth import current_active_user
from app.infra.vault import AppSecrets
from app.repositories import exam_repo
from app.repositories.orm import UserORM
from app.services import grading_service

router = APIRouter(prefix="/exams", tags=["grading"])


class AnswerPart(BaseModel):
    part: str
    answer: str
    submitted_at: datetime


class ExerciseAnswer(BaseModel):
    exercise_id: int
    parts: list[AnswerPart]


class SubmitRequest(BaseModel):
    answers: list[ExerciseAnswer]


# NOTE: registered BEFORE the exams router in main.py so this literal /history
# route is not shadowed by the exams router's GET /{session_id} param route.
@router.get("/history")
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


@router.post("/{session_id}/submit")
async def submit_answers(
    session_id: UUID,
    body: SubmitRequest,
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
    secrets: AppSecrets = Depends(get_secrets),
):
    answers = [a.model_dump(mode="json") for a in body.answers]
    # Pre-flight validation runs HERE (awaited) so ExamNotFound/SessionExpired/
    # InvalidAnswerSubmission map to 404/410/422 before any 200 is sent. Raising
    # inside the StreamingResponse generator would fire after headers are committed.
    exam_content, answer_key = await grading_service.validate_submission(
        session_id, user.id, answers, db_session
    )
    return StreamingResponse(
        grading_service.submit_answers(
            session_id=session_id,
            user_id=user.id,
            answers=answers,
            exam_content=exam_content,
            answer_key=answer_key,
            db_session=db_session,
            secrets=secrets,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{session_id}/results")
async def get_results(
    session_id: UUID,
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
):
    result = await grading_service.get_results(session_id, user.id, db_session)
    return result.model_dump(mode="json")
