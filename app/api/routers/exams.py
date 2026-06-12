"""POST /exams/generate, GET /exams/sessions, GET /exams/active, GET /exams/{session_id},
POST /exams/{session_id}/extract-answers."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
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


@router.get("/sessions")
async def list_exam_sessions(
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
):
    sessions = await exam_service.list_sessions(user.id, db_session)
    return [
        {
            "session_id": str(s.id),
            "session_type": s.session_type,
            "status": s.status,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]


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
    }


_MIME_ALIASES: dict[str, str] = {
    "image/jpg": "image/jpeg",
    "image/jpe": "image/jpeg",
    "image/jfif": "image/jpeg",
    "image/pjpeg": "image/jpeg",
    "image/x-png": "image/png",
}
_EXT_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
}


@router.post("/{session_id}/extract-answers")
async def extract_exam_answers(
    session_id: UUID,
    file: UploadFile = File(...),
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
    secrets: AppSecrets = Depends(get_secrets),
):
    import os
    file_bytes = await file.read()
    mime_type = _MIME_ALIASES.get(file.content_type or "", file.content_type or "")
    # Fall back to extension-based detection when content_type is absent or unrecognised
    if not mime_type and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        mime_type = _EXT_MIME.get(ext, "")
    return await exam_service.extract_answers(
        session_id=session_id,
        user_id=user.id,
        file_bytes=file_bytes,
        mime_type=mime_type,
        db_session=db_session,
        secrets=secrets,
    )


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
    }
