"""POST /chat — SSE streaming chat with NeMo Guardrails."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session, get_redis, get_secrets
from app.infra.auth import current_active_user
from app.infra.vault import AppSecrets
from app.repositories.orm import UserORM
from app.repositories import message_repo
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
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
    attached: UUID | None = None
    if body.attached_session_id:
        try:
            attached = UUID(body.attached_session_id)
        except ValueError:
            pass

    return StreamingResponse(
        chat_service.handle_turn(
            message=body.message,
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


@router.get("/history")
async def get_history(
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
):
    conv = await message_repo.get_or_create_conversation(db_session, user.id, "math_gs12")
    await db_session.commit()
    messages = await message_repo.get_messages(db_session, conv.id, limit=100)
    return [{"role": msg.role.value, "content": msg.content} for msg in messages]


@router.post("/clear", status_code=204)
async def clear_chat(
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
    secrets: AppSecrets = Depends(get_secrets),
):
    await chat_service.clear_chat(
        user_id=user.id,
        db_session=db_session,
        redis=redis,
    )
