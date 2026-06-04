"""GET /health — checks Vault, DB, and Redis connectivity."""
import os

import hvac
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session, get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    status: dict[str, str] = {}
    overall_ok = True

    # ── Vault ─────────────────────────────────────────────────────────────────
    try:
        vault_addr = os.environ.get("VAULT_ADDR", "http://vault:8200")
        vault_token = os.environ.get("VAULT_TOKEN", "")
        client = hvac.Client(url=vault_addr, token=vault_token)
        status["vault"] = "connected" if client.is_authenticated() else "unreachable"
        if status["vault"] != "connected":
            overall_ok = False
    except Exception:
        status["vault"] = "unreachable"
        overall_ok = False

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        await session.execute(text("SELECT 1"))
        status["db"] = "connected"
    except Exception:
        status["db"] = "unreachable"
        overall_ok = False

    # ── Redis ─────────────────────────────────────────────────────────────────
    try:
        await redis.ping()
        status["redis"] = "connected"
    except Exception:
        status["redis"] = "unreachable"
        overall_ok = False

    http_status = 200 if overall_ok else 503
    return JSONResponse(
        status_code=http_status,
        content={"status": "ok" if overall_ok else "degraded", **status},
    )
