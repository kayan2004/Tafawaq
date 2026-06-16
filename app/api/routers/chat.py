"""POST /chat — SSE streaming chat with NeMo Guardrails.
GET /chat/sessions, POST /chat/sessions — named conversation thread management.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session, get_redis, get_secrets
from app.domain.exceptions import ConversationNotFound
from app.domain.models import ChatSession
from app.infra.auth import current_active_user
from app.infra.vault import AppSecrets
from app.repositories.orm import UserORM
from app.repositories import message_repo
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])

_ALLOWED_SUBJECTS: frozenset[str] = frozenset({"math_gs12"})


def _to_chat_session(row: "message_repo.ConversationORM") -> ChatSession:  # type: ignore[name-defined]
    return ChatSession(
        id=row.id,
        subject=row.subject or "",
        title=row.title,
        created_at=row.created_at,
        last_message_at=row.last_message_at,
    )


# ── Session management ────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
) -> list[ChatSession]:
    rows = await message_repo.list_conversations(db_session, user.id)
    return [_to_chat_session(r) for r in rows]


class CreateSessionRequest(BaseModel):
    subject: str
    title: str | None = None


@router.post("/sessions", status_code=201)
async def create_session(
    body: CreateSessionRequest,
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
) -> ChatSession:
    if body.subject not in _ALLOWED_SUBJECTS:
        raise HTTPException(status_code=422, detail=f"Unknown subject '{body.subject}'.")
    title = body.title.strip() if body.title and body.title.strip() else None
    row = await message_repo.create_named_conversation(db_session, user.id, body.subject, title)
    await db_session.commit()
    await db_session.refresh(row)
    return _to_chat_session(row)


class RenameChatSessionRequest(BaseModel):
    title: str


@router.patch("/sessions/{conversation_id}", status_code=200)
async def rename_session(
    conversation_id: str,
    body: RenameChatSessionRequest,
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
) -> ChatSession:
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id.")
    conv = await message_repo.get_conversation_for_user(db_session, conv_uuid, user.id)
    if conv is None:
        raise ConversationNotFound("Chat session not found.")
    title = body.title.strip() or None
    await message_repo.rename_conversation(db_session, conv_uuid, title)
    await db_session.commit()
    await db_session.refresh(conv)
    return _to_chat_session(conv)


# ── Chat stream ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    attached_session_id: str | None = None
    image_base64: str | None = None
    image_media_type: str | None = None


@router.post("")
async def chat(
    body: ChatRequest,
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
    secrets: AppSecrets = Depends(get_secrets),
):
    try:
        conv_uuid = UUID(body.conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id.")

    # Ownership check must happen before StreamingResponse is constructed — once
    # the SSE stream starts (200 + headers sent) we can no longer return 4xx.
    conv = await message_repo.get_conversation_for_user(db_session, conv_uuid, user.id)
    if conv is None:
        raise ConversationNotFound("Chat session not found.")

    attached: UUID | None = None
    if body.attached_session_id:
        try:
            attached = UUID(body.attached_session_id)
        except ValueError:
            pass

    return StreamingResponse(
        chat_service.handle_turn(
            message=body.message,
            conversation_id=conv_uuid,
            user_id=user.id,
            is_admin=user.is_superuser,
            secrets=secrets,
            db_session=db_session,
            redis=redis,
            attached_session_id=attached,
            image_base64=body.image_base64,
            image_media_type=body.image_media_type,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/history")
async def get_history(
    conversation_id: str = Query(...),
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
):
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id.")
    conv = await message_repo.get_conversation_for_user(db_session, conv_uuid, user.id)
    if conv is None:
        raise ConversationNotFound("Chat session not found.")
    messages = await message_repo.get_messages(db_session, conv_uuid, limit=100)
    return [{"role": msg.role.value, "content": msg.content} for msg in messages]


# ── Clear ─────────────────────────────────────────────────────────────────────

class ClearChatRequest(BaseModel):
    conversation_id: str


@router.post("/clear", status_code=204)
async def clear_chat(
    body: ClearChatRequest,
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
    secrets: AppSecrets = Depends(get_secrets),
):
    try:
        conv_uuid = UUID(body.conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id.")
    conv = await message_repo.get_conversation_for_user(db_session, conv_uuid, user.id)
    if conv is None:
        raise ConversationNotFound("Chat session not found.")
    await chat_service.clear_chat(
        conversation_id=conv_uuid,
        db_session=db_session,
        redis=redis,
    )
