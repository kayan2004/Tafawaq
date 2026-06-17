"""Subject-agnostic handwritten answer extraction prompt."""
from __future__ import annotations


def build_extraction_prompt(exam_content: dict) -> str:
    lines = [
        "You are analyzing a scanned handwritten exam response.",
        "Extract the student's written answers and map them to the exercise parts listed below.",
        "",
        "## Exam Structure",
    ]

    for ex in exam_content.get("exercises", []):
        lines.append(
            f"\n### Exercise {ex['id']} — {ex.get('topic', '')} ({ex.get('total_marks', '?')} marks)"
        )
        if ex.get("content"):
            lines.append(f"Stem: {ex['content'][:300]}")
        for p in ex.get("parts", []):
            lines.append(
                f"  Part \"{p['part']}\" ({p.get('marks', '?')} marks): {p.get('content', '')[:200]}"
            )

    lines += [
        "",
        "## Instructions",
        "1. Match handwritten numbering to the exercise/part IDs in the structure above.",
        "2. Extract ONLY the student's final answer for each part (not full working steps). Keep it concise.",
        "3. For parts that are illegible, blank, or missing, use an empty string \"\".",
        "4. Preserve mathematical notation: use LaTeX where clearly written (e.g. \\\\frac{1}{2}, x^2).",
        "5. Return ONLY valid JSON — no markdown code fences, no explanation.",
        "",
        "## Response format (fill in all exercise IDs and part IDs from the structure above)",
        '{',
        '  "answers": [',
        '    {',
        '      "exercise_id": 1,',
        '      "parts": [',
        '        { "part": "a", "answer": "extracted text or empty string" }',
        '      ]',
        '    }',
        '  ]',
        '}',
        "",
        "Include every exercise and every part listed above. Use the exact same exercise_id integers and part strings.",
    ]

    return "\n".join(lines)
