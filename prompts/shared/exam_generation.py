"""Subject-agnostic exam generation prompts."""
from __future__ import annotations

JUDGE_SYSTEM_PROMPT = (
    "You are a solution checker. Compare a student's solution to an official answer key "
    "and determine whether they reach the same correct final answers. "
    'Reply with JSON only: {"agrees": true|false, "notes": "brief explanation"}'
)
