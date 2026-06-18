"""Pydantic domain models.

These are the types that cross layer boundaries — services return them,
repositories accept and return them. ORM models MUST NOT appear here.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import Branch, Language, SessionStatus, SessionType


# ── User profile details ─────────────────────────────────────────────────────

class UserDetails(BaseModel):
    user_id: UUID
    language: Language
    grade: int
    branch: Branch | None = None
    updated_at: datetime


# ── Exam content ─────────────────────────────────────────────────────────────

class ExamPart(BaseModel):
    part: str       # "1", "2", "3", "a", "b", etc.
    marks: float
    content: str    # LaTeX string

class ExamExercise(BaseModel):
    id: int
    topic: str
    total_marks: float
    content: str    # exercise stem with LaTeX
    parts: list[ExamPart]
    is_validated: bool = True
    validation_notes: str = ""

class ExamContent(BaseModel):
    exercises: list[ExamExercise] = []

class AnswerKeyPart(BaseModel):
    part: str
    marks: float
    answer: str
    partial_credit: str = ""

class AnswerKeyExercise(BaseModel):
    id: int
    parts: list[AnswerKeyPart]

class AnswerKey(BaseModel):
    exercises: list[AnswerKeyExercise] = []


# ── Official exam (shared past exam, not per-user) ───────────────────────────

class OfficialExam(BaseModel):
    id: UUID
    year: int
    session_label: str
    exam_content: ExamContent
    created_at: datetime


# ── Chat sessions (named conversation threads) ────────────────────────────────

class ChatSession(BaseModel):
    id: UUID
    subject: str
    title: str | None
    created_at: datetime
    last_message_at: datetime | None


# ── Session ───────────────────────────────────────────────────────────────────

class ExamSession(BaseModel):
    id: UUID
    user_id: UUID
    session_type: SessionType
    status: SessionStatus
    exam_content: ExamContent
    created_at: datetime


# ── Past questions ────────────────────────────────────────────────────────────

class PastQuestion(BaseModel):
    chunk_id: UUID
    year: int
    session: int
    exercise_id: int
    topic: str
    question_type: str
    marks: float
    content: str
    answer: str | None = None      # populated when source_type = answer_key
    similarity_score: float | None = None


# ── Topic analytics ───────────────────────────────────────────────────────────

class TopicStat(BaseModel):
    topic: str
    appearances: int
    last_seen_year: int
    last_seen_session: int
    frequency_tier: str            # "high" | "medium" | "low" — computed, not stored


# ── Textbook ─────────────────────────────────────────────────────────────────

class TextbookPageMeta(BaseModel):
    page_number: int
    chapter: str
    section: str
    page_type: str


class TextbookPage(BaseModel):
    page_number: int
    chapter: str
    section: str
    page_type: str
    content: str


# ── Error response (FR-026, Constitution Principle IV) ────────────────────────

class ErrorResponse(BaseModel):
    error: str
    request_id: str
