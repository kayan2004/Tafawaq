"""User profile details — GET and PUT /auth/me/details."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session
from app.domain.enums import Branch, Language
from app.domain.exceptions import UserDetailsNotFound
from app.domain.models import UserDetails
from app.infra.auth import current_active_user
from app.repositories.orm import UserORM
from app.repositories.user_details_repo import get_user_details, upsert_user_details

router = APIRouter(prefix="/auth/me", tags=["profile"])


class UserDetailsRequest(BaseModel):
    language: Language
    grade: int
    branch: Branch | None = None

    @model_validator(mode="after")
    def validate_grade_branch(self) -> "UserDetailsRequest":
        if self.grade not in (9, 12):
            raise ValueError("grade must be 9 or 12")
        if self.grade == 12 and self.branch is None:
            raise ValueError("branch is required for grade 12")
        if self.grade == 9 and self.branch is not None:
            raise ValueError("branch must be null for grade 9")
        return self


class UserDetailsResponse(BaseModel):
    language: Language
    grade: int
    branch: Branch | None = None

    @classmethod
    def from_domain(cls, d: UserDetails) -> "UserDetailsResponse":
        return cls(language=d.language, grade=d.grade, branch=d.branch)


@router.get("/details", response_model=UserDetailsResponse)
async def get_my_details(
    user: UserORM = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> UserDetailsResponse:
    details = await get_user_details(session, user.id)
    if details is None:
        raise UserDetailsNotFound("Profile not set up yet.")
    return UserDetailsResponse.from_domain(details)


@router.put("/details", response_model=UserDetailsResponse)
async def upsert_my_details(
    body: UserDetailsRequest,
    user: UserORM = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> UserDetailsResponse:
    details = await upsert_user_details(
        session, user.id, body.language, body.grade, body.branch
    )
    return UserDetailsResponse.from_domain(details)
