"""Auth router — register, login, logout, me.

fastapi-users routers handle all endpoint logic.
"""
import uuid

from fastapi_users import schemas

from app.infra.auth import auth_backend, fastapi_users
from app.repositories.orm import UserORM


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


# Routers provided by fastapi-users
auth_router = fastapi_users.get_auth_router(auth_backend)
register_router = fastapi_users.get_register_router(UserRead, UserCreate)
users_router = fastapi_users.get_users_router(UserRead, UserUpdate)
