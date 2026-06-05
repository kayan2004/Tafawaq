"""FastAPI application entry point.

Lifespan resolves all secrets from Vault at startup — the app refuses
to boot if Vault is unreachable (Constitution Principle II).
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from redis.asyncio import Redis, from_url

from app.domain.exceptions import VaultUnavailable
from app.infra.vault import resolve_secrets


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Secrets (fail-fast if Vault unreachable) ──────────────────────────────
    try:
        secrets = resolve_secrets()
    except VaultUnavailable as exc:
        # Re-raise — process exits before serving any request.
        raise SystemExit(f"[startup] Vault unavailable: {exc}") from exc

    app.state.secrets = secrets

    # ── Redis connection pool ─────────────────────────────────────────────────
    redis: Redis = from_url(
        f"redis://redis:6379",
        encoding="utf-8",
        decode_responses=True,
    )
    app.state.redis = redis

    yield

    # ── Cleanup ───────────────────────────────────────────────────────────────
    await redis.aclose()


app = FastAPI(
    title="Lebanese Math Coach",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Request ID middleware (Constitution Principle IV) ─────────────────────────

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Exception handlers are registered in app/api/exceptions.py ───────────────
# ── Routers are registered below after auth is wired ─────────────────────────

from app.api import exceptions as _exc_handlers  # noqa: E402, F401
from app.api.routers import health as _health  # noqa: E402, F401
from app.api.routers import questions as _questions  # noqa: E402, F401
from app.api.routers import topics as _topics  # noqa: E402, F401
from app.api.routers.auth import auth_router, register_router, users_router  # noqa: E402

app.include_router(_health.router)
app.include_router(auth_router, prefix="/auth/jwt", tags=["auth"])
app.include_router(register_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/auth", tags=["auth"])
app.include_router(_questions.router)
app.include_router(_topics.router)
