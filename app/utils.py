"""Shared utility functions used across app/ layers."""
from __future__ import annotations

import json


def parse_json_response(raw: str) -> dict:
    """Strip markdown code fences from a Claude response and parse the JSON."""
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[-1]
        if clean.endswith("```"):
            clean = clean[: clean.rfind("```")]
    return json.loads(clean.strip())
