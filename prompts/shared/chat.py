"""Subject-agnostic chat utilities."""
from __future__ import annotations


def build_retrieve_user_message(student_question: str, candidates: list[dict]) -> str:
    lines = [f"STUDENT QUESTION:\n{student_question}\n\nCANDIDATES:"]
    for i, c in enumerate(candidates, 1):
        lines.append(
            f"\n--- Candidate {i} ---"
            f"\nYear: {c['year']}  Session: {c['session']}  Marks: {c['marks']}"
            f"\nContent:\n{c['content']}"
        )
    return "\n".join(lines)
