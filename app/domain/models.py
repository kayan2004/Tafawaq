"""Pydantic domain models.

These are the types that cross layer boundaries — services return them,
repositories accept and return them. ORM models MUST NOT appear here.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import SessionStatus, SessionType


# ── Exam content ─────────────────────────────────────────────────────────────

class ExercisePart(BaseModel):
    part: str
    marks: float
    content: str


class GraphSpec(BaseModel):
    type: str                  # e.g. "desmos"
    expression: str
    x_range: list[float]
    y_range: list[float]


class Exercise(BaseModel):
    id: int
    topic: str
    total_marks: float
    content: str
    graph: GraphSpec | None = None
    parts: list[ExercisePart]


class ExamContent(BaseModel):
    exercises: list[Exercise]


# ── Session ───────────────────────────────────────────────────────────────────

class ExamSession(BaseModel):
    id: UUID
    user_id: UUID
    session_type: SessionType
    status: SessionStatus
    exam_content: ExamContent
    created_at: datetime
    expires_at: datetime


# ── Evaluation ────────────────────────────────────────────────────────────────

class EvaluatorScore(BaseModel):
    scores: dict[str, float]       # {"Q1_1": 2.0, "Q1_2": 1.0, ...}
    total: float
    feedback: str
    missing_keywords: list[str]


class EvaluationResult(BaseModel):
    session_id: UUID
    evaluator_1: EvaluatorScore
    evaluator_2: EvaluatorScore
    total_score_1: float
    total_score_2: float
    discrepancy_flagged: bool
    discrepancy_details: str | None = None


# ── Past questions ────────────────────────────────────────────────────────────

class PastQuestion(BaseModel):
    chunk_id: UUID
    year: int
    session: int
    exercise_id: int
    topic: str
    subtopic: str
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


# ── Error response (FR-026, Constitution Principle IV) ────────────────────────

class ErrorResponse(BaseModel):
    error: str
    request_id: str
