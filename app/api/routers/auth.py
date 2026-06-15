"""Auth router — register, login, logout, me.

fastapi-users routers handle all endpoint logic.
"""
import uuid

from fastapi_users import schemas

from app.infra.auth import auth_backend, fastapi_users
from app.repositories.orm import UserORM


class UserRead(schemas.BaseUser[uuid.UUID]):
    name: str | None = None


class UserCreate(schemas.BaseUserCreate):
    name: str | None = None


class UserUpdate(schemas.BaseUserUpdate):
    name: str | None = None


# Routers provided by fastapi-users
auth_router = fastapi_users.get_auth_router(auth_backend)
register_router = fastapi_users.get_register_router(UserRead, UserCreate)
users_router = fastapi_users.get_users_router(UserRead, UserUpdate)
