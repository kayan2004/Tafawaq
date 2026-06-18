"""Seed Langfuse with every prompt in the prompts/ directory.

Two categories, handled differently:

1. Static prompts (plain string / dict-of-string constants whose name ends in
   _PROMPT or _SYSTEM, e.g. RETRIEVE_SYSTEM_PROMPT, PERSONA_INSTRUCTIONS) are
   pushed under explicit names that exactly match what the service layer
   fetches at runtime via langfuse_client.get_prompt(). STATIC_PROMPT_NAMES
   below is the single source of truth for that name mapping — if you add a
   new runtime get_prompt() call, add its constant here too, or the seeded
   prompt will never be created and the call will silently always use its
   local fallback.

2. Dynamic prompts (the big build_*() functions for chat/exam
   generation/grading) mix literal braces (JSON schema, LaTeX like
   $\\frac{2}{...}$) with their own f-string interpolation, which collides
   with Langfuse's {{mustache}} variable syntax. Converting them risks
   silently corrupting the highest-value, best-tuned prompts in this app.
   So: the local Python builders remain the runtime source of truth, and we
   seed a *rendered snapshot* of each (using the same data files the
   services use) purely for version history / visibility in the Langfuse UI.
   These are clearly suffixed "_snapshot" and are never fetched at runtime.

Anything else discovered while walking prompts/ (e.g. BLOCK_MESSAGE, the
ingestion tagging prompts) is seeded too, under an auto-generated name, for
completeness — these aren't fetched anywhere either, they're just visibility.

Idempotent: a prompt is only (re)created when its rendered text actually
changed since the last "production" version; unchanged prompts are skipped.

Usage:
    python scripts/seed_langfuse_prompts.py
"""
from __future__ import annotations

import importlib
import json
import pkgutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from langfuse import Langfuse  # noqa: E402

from app.infra.vault import resolve_secrets  # noqa: E402

_LABEL = "production"
_PROMPT_SUFFIXES = ("_PROMPT", "_SYSTEM")

# (module relative name in prompts/, attribute path) -> exact Langfuse prompt
# name used by langfuse_client.get_prompt() call sites in app/.
# Keys use the path relative to prompts/ (e.g. "math/chat" for prompts/math/chat.py).
# Values are the flat Langfuse names — kept stable so existing prompt versions are
# not orphaned when files move between directories.
STATIC_PROMPT_NAMES: dict[tuple[str, str], str] = {
    # ── Fetched at runtime (get_prompt call sites in app/) ─────────────────────
    ("math/chat", "IMAGE_EXTRACT_PROMPT"): "chat_image_extract_prompt",
    ("math/chat", "RETRIEVE_SYSTEM_PROMPT"): "chat_retrieve_system_prompt",
    ("math/grading", "PERSONA_INSTRUCTIONS.strict"): "grading_persona_strict",
    ("math/grading", "PERSONA_INSTRUCTIONS.lenient"): "grading_persona_lenient",
    ("math/exam_generation", "VALIDATOR_SYSTEM_PROMPT"): "exam_validator_system",
    ("math/exam_generation", "REGENERATE_SYSTEM_PROMPT"): "exam_regenerate_system",
    ("shared/exam_generation", "JUDGE_SYSTEM_PROMPT"): "exam_judge_system",
    # ── Visibility only (not fetched at runtime) ────────────────────────────────
    ("math/official_exam_parsing", "SYSTEM_PROMPT"): "official_exam_parsing_system_prompt",
    ("math/official_exam_parsing", "EXTRACTION_SYSTEM_PROMPT"): "official_exam_parsing_extraction_system_prompt",
    ("math/tagging_past_exams", "TAG_PROMPT"): "tagging_past_exams_tag_prompt",
}


def _iter_prompt_modules():
    """Yield (relative_module_name, module) for every .py file in prompts/,
    preserving subdirectory structure as part of the name (e.g. "math/grading"
    for prompts/math/grading.py) — there are no subdirectories today, but the
    walk supports them if that changes."""
    import prompts

    pkg_path = Path(prompts.__file__).parent
    for _finder, name, is_pkg in pkgutil.walk_packages([str(pkg_path)], prefix="prompts."):
        if is_pkg:
            continue
        module = importlib.import_module(name)
        rel = name[len("prompts."):].replace(".", "/")
        yield rel, module


def _discover_static_prompts() -> dict[str, str]:
    """Walk prompts/, return {langfuse_name: text} for every static prompt found."""
    found: dict[str, str] = {}
    for rel_name, module in _iter_prompt_modules():
        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue
            value = getattr(module, attr_name)
            if isinstance(value, str) and attr_name.endswith(_PROMPT_SUFFIXES):
                mapped = STATIC_PROMPT_NAMES.get((rel_name, attr_name))
                name = mapped or f"{rel_name}_{attr_name}".lower()
                found[name] = value
            elif isinstance(value, dict) and value and all(isinstance(v, str) for v in value.values()):
                for key, text in value.items():
                    mapped = STATIC_PROMPT_NAMES.get((rel_name, f"{attr_name}.{key}"))
                    name = mapped or f"{rel_name}_{attr_name}_{key}".lower()
                    found[name] = text
    return found


def _sample_exam_and_answers() -> tuple[dict, dict, list[dict]]:
    """Minimal realistic exam/answer-key/answers for rendering grading snapshots."""
    exam_content = {
        "exercises": [
            {
                "id": 1,
                "topic": "Functions",
                "total_marks": 5.0,
                "content": "Let f(x) = e^x - x.",
                "parts": [{"part": "1", "marks": 2.0, "content": "Compute f'(x)."}],
            }
        ]
    }
    answer_key = {
        "exercises": [
            {"id": 1, "parts": [{"part": "1", "marks": 2.0, "answer": "f'(x) = e^x - 1", "partial_credit": ""}]}
        ]
    }
    answers = [{"exercise_id": 1, "parts": [{"part": "1", "answer": "e^x - 1"}]}]
    return exam_content, answer_key, answers


def _render_dynamic_snapshots() -> dict[str, str]:
    """Render the big builder functions once, with the same data the services
    load, for version-history visibility only (never fetched at runtime)."""
    data_dir = _REPO_ROOT / "app" / "data"
    curriculum = json.loads((data_dir / "curriculum.json").read_text())
    exam_analysis = json.loads((data_dir / "exam_analysis.json").read_text())
    exam_config = json.loads((data_dir / "exam_config.json").read_text())
    fs_exam_path = data_dir / "2021_regular_exam.md"
    few_shot = [fs_exam_path.read_text()] if fs_exam_path.exists() else []

    from prompts.math.chat import build_chat_system_prompt
    from prompts.math.exam_generation import build_generation_system_prompt
    from prompts.shared.extraction import build_extraction_prompt
    from prompts.math.grading import PERSONA_INSTRUCTIONS, build_pdf_evaluator_prompt
    from prompts.shared.grading import build_evaluator_prompt

    exam_content, answer_key, answers = _sample_exam_and_answers()

    return {
        "chat_system_prompt_snapshot": build_chat_system_prompt(curriculum, counter=0),
        "exam_generation_system_prompt_snapshot": build_generation_system_prompt(
            curriculum, exam_analysis, exam_config, few_shot
        ),
        "exam_extraction_prompt_snapshot": build_extraction_prompt(exam_content),
        "grading_evaluator_prompt_snapshot": build_evaluator_prompt(
            PERSONA_INSTRUCTIONS["strict"], exam_content, answer_key, answers
        ),
        "grading_pdf_evaluator_prompt_snapshot": build_pdf_evaluator_prompt(
            PERSONA_INSTRUCTIONS["strict"], exam_content, answers
        ),
    }


def _existing_text(client: Langfuse, name: str) -> str | None:
    try:
        return client.get_prompt(name, label=_LABEL).prompt
    except Exception:
        return None


def _seed_one(client: Langfuse, name: str, text: str) -> str:
    """Returns 'created', 'updated', or 'skipped'."""
    current = _existing_text(client, name)
    if current == text:
        return "skipped"
    client.create_prompt(name=name, prompt=text, labels=[_LABEL], type="text")
    return "created" if current is None else "updated"


def main() -> None:
    secrets = resolve_secrets()
    if not secrets.langfuse_public_key or not secrets.langfuse_secret_key:
        print("Langfuse keys not configured in Vault — nothing to seed.")
        sys.exit(1)

    import os
    host = os.environ.get("LANGFUSE_HOST", "http://langfuse:3000")
    client = Langfuse(
        public_key=secrets.langfuse_public_key,
        secret_key=secrets.langfuse_secret_key,
        host=host,
    )

    static_prompts = _discover_static_prompts()
    dynamic_snapshots = _render_dynamic_snapshots()
    all_prompts = {**static_prompts, **dynamic_snapshots}

    results: dict[str, list[str]] = {"created": [], "updated": [], "skipped": []}
    for name, text in sorted(all_prompts.items()):
        status = _seed_one(client, name, text)
        results[status].append(name)

    client.flush()

    print(f"\nSeeded {len(all_prompts)} prompts to Langfuse (label={_LABEL}):\n")
    for status in ("created", "updated", "skipped"):
        names = results[status]
        print(f"  {status} ({len(names)}):")
        for name in names:
            print(f"    - {name}")
    print()


if __name__ == "__main__":
    main()
