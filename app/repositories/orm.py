"""SQLAlchemy ORM models.

These models MUST NOT be imported by services/, api/, or domain/.
They exist exclusively within repositories/ (Constitution Principle I).

UserORM extends fastapi-users BaseUser and is the single source of truth
for the User entity — no separate User model exists elsewhere.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as SAUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import MessageRole, QuestionType, SessionStatus, SessionType


class Base(DeclarativeBase):
    pass


# ── Users (extends fastapi-users base) ───────────────────────────────────────

class UserORM(SQLAlchemyBaseUserTableUUID, Base):
    """Single User entity. fastapi-users BaseUser provides id, email, hashed_password,
    is_active, is_superuser, is_verified columns."""
    __tablename__ = "users"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Conversations ─────────────────────────────────────────────────────────────

class ConversationORM(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list[MessageORM]] = relationship("MessageORM", back_populates="conversation")


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageORM(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    guardrails_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    conversation: Mapped[ConversationORM] = relationship("ConversationORM", back_populates="messages")


# ── Exam Sessions ─────────────────────────────────────────────────────────────

class ExamSessionORM(Base):
    __tablename__ = "exam_sessions"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_type: Mapped[SessionType] = mapped_column(SAEnum(SessionType), nullable=False)
    exam_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    answer_key: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus), nullable=False, default=SessionStatus.in_progress
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── Exam Results (permanent — no expires_at per FR-025) ──────────────────────

class ExamResultORM(Base):
    __tablename__ = "exam_results"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("exam_sessions.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    student_answers: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evaluator_1: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evaluator_2: Mapped[dict] = mapped_column(JSONB, nullable=False)
    total_score_1: Mapped[float] = mapped_column(Float, nullable=False)
    total_score_2: Mapped[float] = mapped_column(Float, nullable=False)
    discrepancy_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False)
    image_path: Mapped[str | None] = mapped_column(String, nullable=True)  # reserved for B1
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # No expires_at — results are permanent (FR-025)


# ── Chunks (pgvector) ─────────────────────────────────────────────────────────

class ChunkORM(Base):
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # past_exam | answer_key
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    session: Mapped[int] = mapped_column(Integer, nullable=False)
    # exercise_id enables answer key pairing: same (year, session, exercise_id)
    # with source_type='answer_key' is the answer key for source_type='past_exam'.
    exercise_id: Mapped[int] = mapped_column(Integer, nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    subtopic: Mapped[str] = mapped_column(String(100), nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(SAEnum(QuestionType), nullable=False)
    marks: Mapped[float] = mapped_column(Float, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Topic Stats ───────────────────────────────────────────────────────────────

class TopicStatsORM(Base):
    __tablename__ = "topic_stats"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    topic: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    subtopic: Mapped[str] = mapped_column(String(100), nullable=False)
    appearances: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_seen_session: Mapped[int] = mapped_column(Integer, nullable=False)
