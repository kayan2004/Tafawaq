"""Admin panel endpoints — all gated on is_superuser, all under /admin/*."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session, get_secrets
from app.infra.auth import current_superuser
from app.infra.vault import AppSecrets
from app.repositories.orm import UserORM
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Overview ────────────────────────────────────────────────────────────────


@router.get("/overview")
async def get_overview(
    _user: UserORM = Depends(current_superuser),
    db_session: AsyncSession = Depends(get_async_session),
):
    return await admin_service.get_overview(db_session)


# ── Past-exam ingestion ────────────────────────────────────────────────────────


@router.get("/ingestion/past-exams")
async def list_past_exam_files(
    _user: UserORM = Depends(current_superuser),
    db_session: AsyncSession = Depends(get_async_session),
):
    files = await admin_service.list_past_exam_files(db_session)
    return {"files": files}


class TriggerPastExamRequest(BaseModel):
    filenames: list[str]


@router.post("/ingestion/past-exams/trigger")
async def trigger_past_exam_ingestion(
    body: TriggerPastExamRequest,
    _user: UserORM = Depends(current_superuser),
    secrets: AppSecrets = Depends(get_secrets),
):
    # Validate before constructing the StreamingResponse — once the SSE stream
    # starts (200 + headers sent) errors can no longer map to a 4xx.
    await admin_service.validate_past_exam_filenames(body.filenames)
    return StreamingResponse(
        admin_service.stream_past_exam_ingestion(body.filenames, secrets),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Textbook ingestion ──────────────────────────────────────────────────────


@router.get("/ingestion/textbook")
async def list_textbook_chapters(
    _user: UserORM = Depends(current_superuser),
    db_session: AsyncSession = Depends(get_async_session),
):
    chapters = await admin_service.list_textbook_chapters(db_session)
    return {"chapters": chapters}


@router.post("/ingestion/textbook/trigger")
async def trigger_textbook_ingestion(
    files: list[UploadFile] = File(...),
    _user: UserORM = Depends(current_superuser),
    secrets: AppSecrets = Depends(get_secrets),
):
    # Read upload contents before constructing the StreamingResponse — FastAPI
    # closes UploadFile streams as soon as this route handler returns, which
    # happens before the generator below resumes past its first yield.
    file_data = [(f.filename or "untitled.md", await f.read()) for f in files]
    return StreamingResponse(
        admin_service.stream_textbook_ingestion(file_data, secrets),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Topics ──────────────────────────────────────────────────────────────────


@router.get("/topics")
async def get_topics(
    _user: UserORM = Depends(current_superuser),
    db_session: AsyncSession = Depends(get_async_session),
):
    return await admin_service.get_topics_with_gaps(db_session)


# ── Guardrails ──────────────────────────────────────────────────────────────


@router.get("/guardrails/summary")
async def get_guardrails_summary(
    _user: UserORM = Depends(current_superuser),
    db_session: AsyncSession = Depends(get_async_session),
):
    return await admin_service.get_guardrails_summary(db_session)


@router.get("/guardrails/messages")
async def get_guardrails_messages(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    _user: UserORM = Depends(current_superuser),
    db_session: AsyncSession = Depends(get_async_session),
):
    messages = await admin_service.get_guardrails_messages(db_session, date_from, date_to)
    return {"messages": messages}


# ── Users ───────────────────────────────────────────────────────────────────


@router.get("/users")
async def list_users(
    _user: UserORM = Depends(current_superuser),
    db_session: AsyncSession = Depends(get_async_session),
):
    users = await admin_service.list_users(db_session)
    return {"users": users}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    _user: UserORM = Depends(current_superuser),
    db_session: AsyncSession = Depends(get_async_session),
):
    await admin_service.deactivate_user(db_session, user_id)
    return {"status": "deactivated"}
