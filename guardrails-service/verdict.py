"""Pure-Python parsing for classifier verdicts — zero external dependencies, so
this module is unit-testable without installing nemoguardrails/anthropic/langchain.

Category string values MUST stay in sync with app.domain.enums.GuardrailCategory
in the main API repo — the two services don't share code, only this JSON contract.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

_VALID_CATEGORIES = {"off_topic", "prompt_injection", "harmful_content"}


@dataclass
class InputVerdict:
    category: str | None
    score: float
    reason: str


@dataclass
class OutputVerdict:
    flagged: bool
    score: float
    reason: str


def _strip_fences(raw: str) -> str:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[-1]
        if clean.endswith("```"):
            clean = clean[: clean.rfind("```")]
    return clean.strip()


def parse_input_verdict(raw: str) -> InputVerdict:
    """Parse the classify_input model response. Fails closed: unparseable -> harmful_content block."""
    try:
        data = json.loads(_strip_fences(raw))
        category = data.get("category")
        if category not in _VALID_CATEGORIES:
            category = None
        return InputVerdict(
            category=category,
            score=float(data.get("score", 0.0)),
            reason=str(data.get("reason", "")),
        )
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        return InputVerdict(
            category="harmful_content",
            score=1.0,
            reason=f"Unparseable classifier response, failing closed: {raw[:80]!r}",
        )


def parse_output_verdict(raw: str) -> OutputVerdict:
    """Parse the classify_output model response. Fails closed: unparseable -> flagged."""
    try:
        data = json.loads(_strip_fences(raw))
        return OutputVerdict(
            flagged=bool(data.get("flagged", False)),
            score=float(data.get("score", 0.0)),
            reason=str(data.get("reason", "")),
        )
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        return OutputVerdict(
            flagged=True,
            score=1.0,
            reason=f"Unparseable classifier response, failing closed: {raw[:80]!r}",
        )
