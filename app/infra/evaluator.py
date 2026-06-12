"""Single evaluator call — always run via asyncio.to_thread()."""
from __future__ import annotations

import json

from app.domain.exceptions import EvaluatorResponseError
from app.domain.grading import EvaluatorResult, ExerciseResult, PartResult
from app.infra.llm.claude import call_claude
from prompts.grading import build_evaluator_prompt, build_pdf_evaluator_prompt


def _strip_fences(raw: str) -> str:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[-1]
        if clean.endswith("```"):
            clean = clean[: clean.rfind("```")]
    return clean.strip()


def call_pdf_evaluator(
    persona: str,
    exam_content: dict,
    pdf_bytes: bytes,
    answers: list[dict],
    api_key: str,
) -> EvaluatorResult:
    """Grade against the official exam PDF (questions + solutions). Always run via asyncio.to_thread()."""
    import base64
    system = build_pdf_evaluator_prompt(persona, exam_content, answers)
    b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": b64,
                    },
                },
                {
                    "type": "text",
                    "text": "Grade the student's answers using the official solutions in this PDF. Return JSON only.",
                },
            ],
        }
    ]
    raw = call_claude(messages, system=system, api_key=api_key, max_tokens=16000)
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
        raise EvaluatorResponseError(f"PDF evaluator returned malformed JSON: {exc}") from exc


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
    raw = call_claude(messages, system=system, api_key=api_key, max_tokens=16000)
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
