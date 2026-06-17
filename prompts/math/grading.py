"""Lebanese GS Grade 12 Math grading personas and PDF evaluator prompt."""
from __future__ import annotations

from prompts.shared.grading import _format_answers, _format_exam

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


def build_pdf_evaluator_prompt(
    persona_instructions: str,
    exam_content: dict,
    answers: list[dict],
) -> str:
    """Prompt for grading an official exam where the PDF contains the worked solutions."""
    answers_text = _format_answers(answers)
    exam_text = _format_exam(exam_content)

    # Build schema example from actual exercise parts so Claude uses the correct labels.
    schema_lines: list[str] = []
    all_part_labels: list[str] = []
    for ex in exam_content.get("exercises", []):
        parts_entries = ", ".join(
            f'"{p["part"]}": {{"score": ..., "max_score": {p["marks"]}, "feedback": "", "correction": ""}}'
            for p in ex.get("parts", [])
        )
        all_part_labels.extend(p["part"] for p in ex.get("parts", []))
        schema_lines.append(
            f'    {{"exercise_id": {ex["id"]}, "parts": {{{parts_entries}}}, '
            f'"exercise_total": ..., "exercise_max": {ex["total_marks"]}}}'
        )
    schema_str = "[\n" + ",\n".join(schema_lines) + "\n  ]"
    part_labels_hint = ", ".join(repr(l) for l in dict.fromkeys(all_part_labels))

    return f"""{persona_instructions}

The attached PDF is an official Lebanese GS Grade 12 Math Baccalaureate exam.
It contains both the exam questions and the official worked solutions.
Grade the student's answers part by part against the official solutions in the PDF.

EXAM STRUCTURE (questions and marks):
{exam_text}

STUDENT ANSWERS:
{answers_text}

Return ONLY a valid JSON object (no prose, no markdown fences) with this exact structure:
{{
  "exercises": {schema_str}
}}

Rules:
- Include every exercise the student answered. Omit exercises with no student answer.
- score must be <= max_score. Fractional marks (0.5) are allowed.
- exercise_total = sum of all part scores. exercise_max = sum of all part max_scores.
- Part keys must match exactly: {part_labels_hint}.
- Compare each part against the corresponding official solution in the PDF.
- feedback: one-sentence evaluator note on why marks were awarded or deducted (empty string if fully correct).
- correction: reproduce the complete correct solution from the PDF for this part — all key steps and final answer. Always populate even if the student was correct.
- Return JSON only — no prose before or after."""
