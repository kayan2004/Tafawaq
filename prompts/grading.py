"""System prompts for the dual-evaluator grading pipeline."""

PERSONA_INSTRUCTIONS: dict[str, str] = {
    "strict": (
        "You are a STRICT examiner for the official Lebanese GS Grade 12 Math "
        "baccalaureate. When in doubt, DEDUCT marks. Require complete, rigorous "
        "justification; penalise missing steps, unstated theorems, and notation errors."
    ),
    "lenient": (
        "You are a LENIENT examiner for the official Lebanese GS Grade 12 Math "
        "baccalaureate. When in doubt, AWARD marks. Reward correct method and "
        "understanding even when the final answer or some steps are imperfect."
    ),
}


def build_evaluator_prompt(
    persona: str,
    exam_content: dict,
    answer_key: dict,
    answers: list[dict],
) -> str:
    exam_text = _format_exam(exam_content)
    answer_key_text = _format_answer_key(answer_key)
    answers_text = _format_answers(answers)
    return f"""{PERSONA_INSTRUCTIONS[persona]}

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
        "1": {{"score": 2.0, "max_score": 3.0, "feedback": "brief comment or empty string"}},
        "2": {{"score": 1.0, "max_score": 2.0, "feedback": ""}}
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
