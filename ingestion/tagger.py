"""Deterministic topic tagging for exam chunks.

Replaces the previous claude-haiku LLM tagger.  No API calls, no progress
file, no rate limits.  The public signature of tag_chunks() is unchanged so
pipeline.py requires no edits — api_key and progress_file are accepted but
ignored.

Topic is set to the chapter title(s) from curriculum.json joined by " / " for
multi-chapter exercises (e.g. "Natural Logarithm / Exponential Function").
Subtopic is left blank; question_type defaults to "calculation" because
question-type classification requires semantic understanding that the
deterministic tagger does not attempt.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ingestion.topic_tagging import (
    chunks_to_units,
    load_taxonomy,
    tag_all_units,
)

logger = logging.getLogger(__name__)

# Loaded once at import time — curriculum.json is stable across a pipeline run.
_TAXONOMY: dict[int, str] = load_taxonomy()


def tag_chunks(
    chunks: list[dict],
    api_key: str = "",
    progress_file: Path | None = None,
) -> list[dict]:
    """Tag each chunk with topic, subtopic, and question_type deterministically.

    Only past_exam chunks receive a topic derived from the curriculum taxonomy.
    answer_key chunks inherit the topic of their matching past_exam exercise
    (same year / session / exercise_id), or keep their existing value if no
    match is found.

    api_key and progress_file are accepted for call-site compatibility but are
    not used.
    """
    # Build tags only from past_exam chunks (answer_key has no exercise header).
    units = chunks_to_units(chunks)
    tags = tag_all_units(units)

    # (year, session, exercise_id) → chapter_ids list
    tag_map: dict[tuple[int, int, int], list[int]] = {
        (t["year"], t["session"], t["exercise_id"]): t["chapter_ids"]
        for t in tags
    }

    tagged = 0
    for chunk in chunks:
        key = (chunk["year"], chunk["session"], chunk["exercise_id"])
        chapter_ids = tag_map.get(key)
        if chapter_ids is not None:
            in_scope = [cid for cid in chapter_ids if cid != 0]
            # Use the first chapter title only — chunks.topic is VARCHAR(100) and
            # multi-chapter detail is stored in question_tags.json, not here.
            chunk["topic"] = (
                _TAXONOMY.get(in_scope[0], f"Chapter {in_scope[0]}")
                if in_scope
                else "OTHER"
            )
            tagged += 1
        else:
            chunk.setdefault("topic", "Unknown")

        chunk.setdefault("subtopic", "")
        chunk.setdefault("question_type", "calculation")

    logger.info(
        "Tagged %d/%d chunks deterministically (%d skipped — no matching past_exam unit)",
        tagged,
        len(chunks),
        len(chunks) - tagged,
    )
    return chunks
