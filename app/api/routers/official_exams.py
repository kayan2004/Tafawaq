"""GET /official-exams, POST /official-exams/{exam_id}/take, GET /official-exams/{exam_id}/pdf."""
from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session, get_redis, get_secrets
from app.infra.auth import current_active_user
from app.infra.minio_client import PAST_EXAMS_BUCKET, get_minio_client, get_pdf_bytes
from app.infra.vault import AppSecrets
from app.repositories.orm import UserORM
from app.services import official_exam_service

router = APIRouter(prefix="/official-exams", tags=["official-exams"])


@router.get("")
async def list_official_exams(
    user: UserORM = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    exams = await official_exam_service.list_official_exams(db)
    return [
        {
            "id": str(e.id),
            "year": e.year,
            "session_label": e.session_label,
            "exam_content": e.exam_content.model_dump(),
            "created_at": e.created_at.isoformat(),
        }
        for e in exams
    ]


@router.post("/{exam_id}/take")
async def take_official_exam(
    exam_id: UUID,
    user: UserORM = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
):
    session_id, exam_content = await official_exam_service.spawn_session(
        db=db,
        redis=redis,
        exam_id=exam_id,
        user_id=user.id,
    )
    return {
        "session_id": session_id,
        "exam_content": exam_content,
    }


@router.get("/{exam_id}/pdf")
async def get_official_exam_pdf(
    exam_id: UUID,
    user: UserORM = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
    secrets: AppSecrets = Depends(get_secrets),
):
    pdf_key = await official_exam_service.get_pdf_key(db, exam_id)
    client = get_minio_client(secrets)
    pdf_bytes = await asyncio.to_thread(get_pdf_bytes, client, PAST_EXAMS_BUCKET, pdf_key)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{pdf_key}"'},
    )
