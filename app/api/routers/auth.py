"""Auth router — register, login, logout, me, password reset/change.

fastapi-users routers handle register/login/me/forgot-password/reset-password.
change-password is custom: fastapi-users has no built-in "verify the current
password before changing it" flow.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users import schemas
from pydantic import BaseModel

from app.infra.auth import UserManager, auth_backend, current_active_user, fastapi_users, get_user_manager
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
reset_password_router = fastapi_users.get_reset_password_router()


# ── Change password (authenticated) ───────────────────────────────────────────

change_password_router = APIRouter()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@change_password_router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    user: UserORM = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
) -> None:
    verified, _ = user_manager.password_helper.verify_and_update(
        body.current_password, user.hashed_password
    )
    if not verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    await user_manager.update(UserUpdate(password=body.new_password), user, safe=True)
