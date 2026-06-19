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
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as SAUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import (
    Branch,
    GuardrailCategory,
    GuardrailDirection,
    GuardrailLevel,
    GuardrailSource,
    Language,
    MessageRole,
    QuestionType,
    SessionStatus,
    SessionType,
)


class Base(DeclarativeBase):
    pass


# ── Users (extends fastapi-users base) ───────────────────────────────────────

class UserORM(SQLAlchemyBaseUserTableUUID, Base):
    """Single User entity. fastapi-users BaseUser provides id, email, hashed_password,
    is_active, is_superuser, is_verified columns."""
    __tablename__ = "users"

    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Conversations ─────────────────────────────────────────────────────────────

class ConversationORM(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    # NULL for exam-session conversations; named subject for chat (e.g. "math_gs12").
    subject: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # User-set title; NULL means auto-name by date on the frontend.
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list[MessageORM]] = relationship("MessageORM", back_populates="conversation")


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageORM(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_id_created_at", "conversation_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[ConversationORM] = relationship("ConversationORM", back_populates="messages")


# ── Guardrail Events ──────────────────────────────────────────────────────────

class GuardrailEventORM(Base):
    __tablename__ = "guardrail_events"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True
    )
    source: Mapped[GuardrailSource] = mapped_column(SAEnum(GuardrailSource), nullable=False)
    direction: Mapped[GuardrailDirection] = mapped_column(SAEnum(GuardrailDirection), nullable=False)
    category: Mapped[GuardrailCategory | None] = mapped_column(SAEnum(GuardrailCategory), nullable=True)
    level: Mapped[GuardrailLevel] = mapped_column(SAEnum(GuardrailLevel), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    text_preview: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


# ── Exam Sessions ─────────────────────────────────────────────────────────────

class ExamSessionORM(Base):
    __tablename__ = "exam_sessions"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    session_type: Mapped[SessionType] = mapped_column(SAEnum(SessionType), nullable=False)
    exam_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    answer_key: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus), nullable=False, default=SessionStatus.in_progress
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Exam Results (permanent — no expires_at per FR-025) ──────────────────────

class ExamResultORM(Base):
    __tablename__ = "exam_results"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("exam_sessions.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
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
    # source_type values: past_exam | answer_key | textbook_theory | textbook_exercise | textbook_self_evaluation
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # NULL for textbook chunks (not applicable outside past-exam source types)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # exercise_id enables answer key pairing: same (year, session, exercise_id)
    # with source_type='answer_key' is the answer key for source_type='past_exam'.
    exercise_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    question_type: Mapped[QuestionType | None] = mapped_column(SAEnum(QuestionType), nullable=True)
    marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Textbook Pages ───────────────────────────────────────────────────────────

class TextbookPageORM(Base):
    __tablename__ = "textbook_pages"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    page_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    chapter: Mapped[str] = mapped_column(String, nullable=False)
    section: Mapped[str] = mapped_column(String, nullable=False)
    # page_type values: theory | exercise | self_evaluation | just_for_fun | preface | blank | mixed
    page_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Official Exams (Lebanese GS past exams — shared, not per-user) ────────────

class OfficialExamORM(Base):
    __tablename__ = "official_exams"
    __table_args__ = (
        UniqueConstraint("year", "session_label", name="uq_official_exams_year_session"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    session_label: Mapped[str] = mapped_column(String(50), nullable=False)
    exam_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    answer_key: Mapped[dict] = mapped_column(JSONB, nullable=False)
    pdf_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── User Details (profile: language, grade, branch) ──────────────────────────

class UserDetailsORM(Base):
    __tablename__ = "user_details"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    language: Mapped[Language] = mapped_column(SAEnum(Language), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    branch: Mapped[Branch | None] = mapped_column(SAEnum(Branch), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ── Topic Stats ───────────────────────────────────────────────────────────────

class TopicStatsORM(Base):
    __tablename__ = "topic_stats"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid4)
    topic: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    appearances: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_seen_session: Mapped[int] = mapped_column(Integer, nullable=False)
