"""Subject-agnostic grading prompt builder and exam formatters."""
from __future__ import annotations


def build_evaluator_prompt(
    persona_instructions: str,
    exam_content: dict,
    answer_key: dict,
    answers: list[dict],
) -> str:
    exam_text = _format_exam(exam_content)
    answer_key_text = _format_answer_key(answer_key)
    answers_text = _format_answers(answers)
    return f"""{persona_instructions}

You will be given the exam (with marks per part), the official answer key, and the student's answers.
Grade each exercise part by part.
For parts the student left blank, assign score 0 and leave feedback empty.

EXAM:
{exam_text}

OFFICIAL ANSWER KEY:
{answer_key_text}

STUDENT ANSWERS:
{answers_text}

Return ONLY a valid JSON object (no prose, no markdown fences) with this exact structure:
{{
  "exercises": [
    {{
      "exercise_id": 1,
      "parts": {{
        "1": {{"score": 2.0, "max_score": 3.0, "feedback": "brief evaluator note or empty string", "correction": "full worked solution for this part"}},
        "2": {{"score": 1.0, "max_score": 2.0, "feedback": "", "correction": "complete correct approach with key steps"}}
      }},
      "exercise_total": 3.0,
      "exercise_max": 5.0
    }}
  ]
}}

Rules:
- Include every exercise the student answered. Omit exercises with no student answer.
- score must be <= max_score. Fractional marks (0.5) are allowed.
- exercise_total = sum of all part scores. exercise_max = sum of all part max_scores.
- The keys in "parts" must match the part labels from the exam (e.g. "1", "2", "a", "b").
- feedback: one-sentence evaluator note on why marks were awarded or deducted (empty string if student was fully correct).
- correction: the complete correct solution for this part — show all key steps, intermediate results, and the final answer. Use plain text with math notation. Always populate this field even if the student answered correctly.
- Return JSON only — no prose before or after."""


def _format_exam(exam_content: dict) -> str:
    lines: list[str] = []
    for ex in exam_content.get("exercises", []):
        lines.append(f"Exercise {ex['id']} — {ex['topic']} ({ex['total_marks']} pts)")
        lines.append(ex["content"])
        for part in ex.get("parts", []):
            lines.append(f"  Part {part['part']} ({part['marks']} pts): {part['content']}")
    return "\n".join(lines) if lines else "(no exam content)"


def _format_answer_key(answer_key: dict) -> str:
    lines: list[str] = []
    for ex in answer_key.get("exercises", []):
        lines.append(f"Exercise {ex['id']}:")
        for part in ex.get("parts", []):
            lines.append(f"  Part {part['part']} ({part['marks']} pts): {part['answer']}")
            if part.get("partial_credit"):
                lines.append(f"    Partial credit: {part['partial_credit']}")
    return "\n".join(lines) if lines else "(no answer key)"


def _format_answers(answers: list[dict]) -> str:
    lines: list[str] = []
    for ex in answers:
        lines.append(f"Exercise {ex['exercise_id']}:")
        for part in ex.get("parts", []):
            lines.append(f"  Part {part['part']}: {part['answer']}")
    return "\n".join(lines) if lines else "(no answers submitted)"
