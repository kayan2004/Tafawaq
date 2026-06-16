"""fastapi-users auth configuration.

This module wires UserManager, JWTStrategy, and FastAPIUsers.
The SQLAlchemy User model is UserORM in app/repositories/orm.py —
NO ORM model is defined here (Constitution Principle I).
"""
from typing import AsyncGenerator
from urllib.parse import urlparse
import uuid

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session
from app.infra.email import send_reset_password_email
from app.infra.vault import AppSecrets
from app.repositories.orm import UserORM

# ── Database adapter ──────────────────────────────────────────────────────────

async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, UserORM)


def _frontend_origin(request: Request | None) -> str:
    """Best-effort origin for building reset-password links.

    The SPA calls these endpoints with fetch(), which sends an Origin header
    on cross-origin requests; same-origin browsers may omit it, so we also
    fall back to Referer before defaulting to the local dev frontend port.
    """
    if request is not None:
        for header in ("origin", "referer"):
            value = request.headers.get(header)
            if value:
                parsed = urlparse(value)
                if parsed.scheme and parsed.netloc:
                    return f"{parsed.scheme}://{parsed.netloc}"
    return "http://localhost:3000"


# ── UserManager ───────────────────────────────────────────────────────────────

class UserManager(UUIDIDMixin, BaseUserManager[UserORM, uuid.UUID]):
    def __init__(self, user_db: SQLAlchemyUserDatabase, secrets: AppSecrets) -> None:
        super().__init__(user_db)
        self.reset_password_token_secret = secrets.reset_password_token_secret
        self._secrets = secrets

    async def on_after_register(self, user: UserORM, request: Request | None = None):
        pass  # hook for post-registration logic (e.g. welcome email)

    async def on_after_forgot_password(
        self, user: UserORM, token: str, request: Request | None = None
    ) -> None:
        reset_url = f"{_frontend_origin(request)}/#reset-password?token={token}"
        await send_reset_password_email(
            to=user.email,
            reset_url=reset_url,
            api_key=self._secrets.resend_api_key,
            from_email=self._secrets.reset_password_from_email,
        )


async def get_user_manager(
    request: Request,
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    secrets: AppSecrets = request.app.state.secrets
    yield UserManager(user_db, secrets)


# ── JWT strategy (secret resolved from app.state at request time) ─────────────

def get_jwt_strategy(request: Request) -> JWTStrategy:
    jwt_secret: str = request.app.state.secrets.jwt_secret
    # 24-hour token lifetime (dev default; documented in spec assumptions)
    return JWTStrategy(secret=jwt_secret, lifetime_seconds=86_400)


bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# ── FastAPIUsers instance ─────────────────────────────────────────────────────

fastapi_users = FastAPIUsers[UserORM, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
