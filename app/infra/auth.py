"""fastapi-users auth configuration.

This module wires UserManager, JWTStrategy, and FastAPIUsers.
The SQLAlchemy User model is UserORM in app/repositories/orm.py —
NO ORM model is defined here (Constitution Principle I).
"""
from typing import AsyncGenerator
import uuid

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session
from app.repositories.orm import UserORM

# ── Database adapter ──────────────────────────────────────────────────────────

async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, UserORM)


# ── UserManager ───────────────────────────────────────────────────────────────

class UserManager(UUIDIDMixin, BaseUserManager[UserORM, uuid.UUID]):
    async def on_after_register(self, user: UserORM, request: Request | None = None):
        pass  # hook for post-registration logic (e.g. welcome email)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)


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
