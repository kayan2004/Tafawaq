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
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str


@router.post("")
async def chat(
    body: ChatRequest,
    user: UserORM = Depends(current_active_user),
    db_session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
    secrets: AppSecrets = Depends(get_secrets),
):
    return StreamingResponse(
        chat_service.handle_turn(
            conversation_id=body.conversation_id,
            message=body.message,
            user_id=user.id,
            secrets=secrets,
            db_session=db_session,
            redis=redis,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
