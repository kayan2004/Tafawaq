"""Pydantic models for the dual-evaluator grading pipeline."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class PartResult(BaseModel):
    score: float
    max_score: float
    feedback: str = ""
    correction: str = ""


class ExerciseResult(BaseModel):
    exercise_id: int
    parts: dict[str, PartResult]
    exercise_total: float
    exercise_max: float


class EvaluatorResult(BaseModel):
    exercises: list[ExerciseResult]
    grand_total: float
    grand_max: float


class GradingResult(BaseModel):
    session_id: UUID
    evaluator_1: EvaluatorResult
    evaluator_2: EvaluatorResult
    discrepancy_flagged: bool
    discrepancy_details: str | None = None
    average_total: float


class CorrectionResult(GradingResult):
    """GradingResult enriched with the exam questions and student's answers for display."""
    exam_content: dict
    student_answers: list[dict]
