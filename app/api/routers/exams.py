"""POST /exams/generate, GET /exams/active, GET /exams/{session_id}."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session, get_redis, get_secrets
from app.domain.enums import SessionType
from app.infra.auth import current_active_user
from app.infra.vault import AppSecrets
from app.repositories.orm import UserORM
from app.services import exam_service

router = APIRouter(prefix="/exams", tags=["exams"])


class GenerateRequest(BaseModel):
    session_type: SessionType = SessionType.mock_generated


@router.post("/generate")
async def generate_exam(
    body: GenerateRequest,
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
    secrets: AppSecrets = Depends(get_secrets),
):
    return StreamingResponse(
        exam_service.generate_exam(
            user_id=user.id,
            secrets=secrets,
            db_session=db_session,
            redis=redis,
            session_type=body.session_type,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/active")
async def get_active_session(
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
):
    session = await exam_service.get_active_session(user.id, db_session)
    return {
        "session_id": str(session.id),
        "session_type": session.session_type,
        "status": session.status,
        "exam_content": session.exam_content.model_dump(),
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
    }


@router.get("/{session_id}")
async def get_session(
    session_id: UUID,
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
):
    session = await exam_service.get_session_by_id(session_id, user.id, db_session)
    return {
        "session_id": str(session.id),
        "session_type": session.session_type,
        "status": session.status,
        "exam_content": session.exam_content.model_dump(),
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
    }
