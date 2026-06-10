"""Single evaluator call — always run via asyncio.to_thread()."""
from __future__ import annotations

import json

from app.domain.exceptions import EvaluatorResponseError
from app.domain.grading import EvaluatorResult, ExerciseResult, PartResult
from app.infra.llm.claude import call_claude
from prompts.grading import build_evaluator_prompt


def _strip_fences(raw: str) -> str:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[-1]
        if clean.endswith("```"):
            clean = clean[: clean.rfind("```")]
    return clean.strip()


def call_evaluator(
    persona: str,
    exam_content: dict,
    answer_key: dict,
    answers: list[dict],
    api_key: str,
) -> EvaluatorResult:
    """Synchronous — always wrap with asyncio.to_thread()."""
    system = build_evaluator_prompt(persona, exam_content, answer_key, answers)
    messages = [{"role": "user", "content": "Grade this submission and return the JSON object only."}]
    raw = call_claude(messages, system=system, api_key=api_key, max_tokens=4096)
    try:
        parsed = json.loads(_strip_fences(raw))
        exercises = [
            ExerciseResult(
                exercise_id=ex["exercise_id"],
                parts={k: PartResult(**v) for k, v in ex["parts"].items()},
                exercise_total=float(ex["exercise_total"]),
                exercise_max=float(ex["exercise_max"]),
            )
            for ex in parsed["exercises"]
        ]
        grand_total = round(sum(ex.exercise_total for ex in exercises), 4)
        grand_max = round(sum(ex.exercise_max for ex in exercises), 4)
        return EvaluatorResult(exercises=exercises, grand_total=grand_total, grand_max=grand_max)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise EvaluatorResponseError(f"Evaluator returned malformed JSON: {exc}") from exc
