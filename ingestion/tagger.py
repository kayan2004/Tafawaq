"""claude-haiku topic/subtopic/question_type tagging per chunk."""
import json
import re
from pathlib import Path

import anthropic

from prompts.tagging_past_exams import TAG_PROMPT


def _chunk_key(chunk: dict) -> str:
    """Globally unique key for a chunk across all exams."""
    return (
        f"{chunk.get('year')}-{chunk.get('session')}"
        f"-{chunk.get('source_type')}-{chunk.get('exercise_id')}"
    )


def tag_chunks(
    chunks: list[dict], api_key: str, progress_file: Path | None = None
) -> list[dict]:
    """Tag each chunk with topic, subtopic, and question_type via claude-haiku.

    Chunks whose topic is already set (non-empty, not "Unknown") are skipped so
    re-runs after partial failures only call the API for unresolved chunks.

    If progress_file is provided, per-chunk progress is saved after each API call
    so a mid-run crash can be resumed without re-tagging completed chunks.
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Load saved progress: maps chunk key → {topic, subtopic, question_type}
    progress: dict[str, dict] = {}
    if progress_file is not None and progress_file.exists():
        try:
            progress = json.loads(progress_file.read_text())
        except Exception:
            progress = {}

    # Apply any cached tags from a previous interrupted run
    for chunk in chunks:
        key = _chunk_key(chunk)
        if key in progress:
            chunk.update(progress[key])

    needs_tag = [c for c in chunks if not c.get("topic") or c["topic"] == "Unknown"]
    already_done = len(chunks) - len(needs_tag)
    if already_done:
        print(
            f"[ingestion] Tagging: {already_done}/{len(chunks)} already tagged, "
            f"{len(needs_tag)} remaining"
        )

    for chunk in needs_tag:
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=128,
                messages=[
                    {
                        "role": "user",
                        "content": TAG_PROMPT.format(content=chunk["content"][:800]),
                    }
                ],
            )
            raw = response.content[0].text
            # Model sometimes wraps JSON in markdown fences — extract the object directly.
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(match.group() if match else raw)
            chunk["topic"] = str(data.get("topic", "Unknown"))
            chunk["subtopic"] = str(data.get("subtopic", ""))
            chunk["question_type"] = str(data.get("question_type", "calculation"))
        except (json.JSONDecodeError, KeyError, IndexError, anthropic.APIError):
            chunk["topic"] = "Unknown"
            chunk["subtopic"] = ""
            chunk["question_type"] = "calculation"

        # Persist progress after every chunk so a crash loses at most one API call
        if progress_file is not None:
            key = _chunk_key(chunk)
            progress[key] = {
                "topic": chunk["topic"],
                "subtopic": chunk["subtopic"],
                "question_type": chunk["question_type"],
            }
            progress_file.write_text(json.dumps(progress))

    return chunks
