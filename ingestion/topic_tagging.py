"""Deterministic topic-tagging pipeline for segmented exam exercise units.

No LLM calls — fully rule-based. Two-layer tagger:
  1. HEADER MATCH: normalize exercise header → exact-match lookup in _HEADER_MAP.
     Single ID = certain; set = ambiguous, resolved by keyword pass.
  2. KEYWORD PASS: scan body text for explicit keyword → chapter-id associations.

Writes app/data/question_tags.json (ground truth; the embedding pipeline must
never overwrite this file). topic_stats is NOT written here — pipeline.py's
refresh_topic_stats() is the sole owner of that table; this script only
produces the per-unit chapter_ids ground truth.

Usage:
    # Read chunks from DB (default — runs against local dev DB):
    uv run python -m ingestion.topic_tagging

    # Read chunks from a pipeline cache file instead:
    uv run python -m ingestion.topic_tagging --chunks-file .ingestion_cache/01_chunks.json

    # Custom DB or output path:
    uv run python -m ingestion.topic_tagging \\
        --db-url postgresql://user:pass@host:5432/lebanese_math \\
        --output path/to/question_tags.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from collections import defaultdict
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent
_CURRICULUM_PATH = _REPO_ROOT / "app" / "data" / "curriculum.json"
_DEFAULT_OUTPUT = _REPO_ROOT / "app" / "data" / "question_tags.json"

# ── Header normalization ───────────────────────────────────────────────────────

# Leading Roman-numeral exercise label, e.g. "III - " or "VII–".
_ROMAN_PREFIX = re.compile(
    r"^(?:IX|VIII|VII|VI|V|IV|III|II|I)\s*[-–]\s*",
    re.IGNORECASE,
)
# Trailing point annotation, e.g. " (4 points)" or "(7 pts)".
_POINTS_SUFFIX = re.compile(
    r"\s*\(\s*\d+(?:\.\d+)?\s*p(?:oint|t)s?\s*\)",
    re.IGNORECASE,
)


def normalize_header(header: str) -> str:
    """Strip roman-numeral prefix and point annotation; return lowercase strip."""
    text = _ROMAN_PREFIX.sub("", header)
    text = _POINTS_SUFFIX.sub("", text)
    return text.strip().lower()


# ── Header map ─────────────────────────────────────────────────────────────────
# Keys: normalized lowercase topic names (exact match after normalize_header()).
# Values: set of candidate chapter IDs.
#   Singleton → certain; multi-element → ambiguous, resolved by keyword pass.
#
# Ground truth for topic names comes from the few_shot_exams JSON files and
# the official_exam_pipeline extraction (field: exercises[*].topic).

_HEADER_MAP: dict[str, set[int]] = {
    # ── Out of scope / pre-reform (ch 0) ──────────────────────────────────────
    "complex numbers": {0},
    "transformations": {0},
    "similitude": {0},
    "isometries": {0},
    "homothety": {0},
    "analytic geometry": {0},
    "conics": {0},
    "matrices": {0},
    "plane geometry": {0},
    "affine geometry": {0},
    # ── Ch 1: Parallelism and Orthogonality in Space ──────────────────────────
    "parallelism and orthogonality in space": {1},
    "parallelism and orthogonality": {1},
    "geometry in space": {1},
    "space geometry": {1},
    "solid geometry": {1},
    # ── Ch 2: Continuous Functions on an Interval ─────────────────────────────
    "continuous functions on an interval": {2},
    "continuous functions": {2},
    "continuity on an interval": {2},
    "continuity": {2},
    # ── Ch 3: Inverse Functions ───────────────────────────────────────────────
    "inverse functions": {3},
    # ── Ch 4: Inverse Trigonometric Functions ─────────────────────────────────
    "inverse trigonometric functions": {4},
    # ── Ch 5: Differential Calculus — L'Hôpital ──────────────────────────────
    "differential calculus": {5},
    "l'hôpital's rule": {5},
    "l'hopital's rule": {5},
    "l'hôpital": {5},
    "l'hopital": {5},
    # ── Ch 6: Natural Logarithm ───────────────────────────────────────────────
    "natural logarithm": {6},
    "logarithmic functions": {6},
    "logarithmic function": {6},
    # ── Ch 7: Exponential Function ────────────────────────────────────────────
    "exponential function": {7},
    "exponential functions": {7},
    # ── Ch 6 + 7 together (common combined header) ────────────────────────────
    "logarithmic and exponential functions": {6, 7},
    "exponential and logarithmic functions": {6, 7},
    "logarithm and exponential": {6, 7},
    # ── Ch 8: Second and Higher Order Derivatives ─────────────────────────────
    "second and higher order derivatives": {8},
    "higher order derivatives": {8},
    "second derivative": {8},
    # ── Ch 9: Numerical Sequences ─────────────────────────────────────────────
    "numerical sequences": {9},
    "sequences": {9},
    # ── Ch 10: Definite Integral — Definition and Properties ──────────────────
    "definite integral": {10},
    "definite integrals": {10},
    "definite integral — definition and properties": {10},
    # ── Ch 11: Integration — Substitution and Even/Odd ────────────────────────
    "integration — substitution and even/odd functions": {11},
    "substitution and even/odd functions": {11},
    "integration by substitution": {11},
    # ── Ch 12: Integration — By Parts and Rational Fractions ──────────────────
    "integration — by parts and rational fractions": {12},
    "by parts and rational fractions": {12},
    "integration by parts": {12},
    "rational fractions": {12},
    # ── Ch 13: Applications of Integration — Area ─────────────────────────────
    "applications of integration — area": {13},
    "applications of integration": {13},
    "area between curves": {13},
    # ── Ambiguous integration headers ─────────────────────────────────────────
    "integration": {10, 11, 12, 13},
    "integral": {10, 11, 12, 13},
    "integrals": {10, 11, 12, 13},
    # ── Ch 14: First Order Differential Equations ─────────────────────────────
    "first order differential equations": {14},
    "first order differential equation": {14},
    # ── Ch 15: Second Order Linear Differential Equations ─────────────────────
    "second order linear differential equations with constant coefficients": {15},
    "second order linear differential equations": {15},
    "second order differential equations": {15},
    # ── Ambiguous differential equation headers ────────────────────────────────
    "differential equations": {14, 15},
    "differential equation": {14, 15},
    # ── Ch 16: Combinations ───────────────────────────────────────────────────
    "combinations": {16},
    "binomial formula": {16},
    # ── Ch 17: Conditional Probability ───────────────────────────────────────
    "conditional probability": {17},
    # ── Ch 18: Random Variables ───────────────────────────────────────────────
    "random variables": {18},
    "random variable": {18},
    "discrete random variables": {18},
    # ── Ambiguous probability/stats headers ───────────────────────────────────
    # Lebanese GS "Probability" exercises routinely span both ch 17 and ch 18.
    "probability": {17, 18},
    "probability and statistics": {17, 18},
    "statistics and probability": {17, 18},
    "probability and combinations": {16, 17},
    "combinations and probability": {16, 17},
    # ── Ambiguous multi-chapter function-study headers ─────────────────────────
    # "Functions" in GS exams is a curve-study exercise spanning ch 2–8.
    "functions": {2, 3, 6, 7, 8},
    "study of a function": {2, 3, 6, 7, 8},
    "functions and curve study": {2, 3, 6, 7, 8},
    "function study": {2, 3, 6, 7, 8},
    "curve study": {2, 3, 6, 7, 8},
}


# ── Keyword map ────────────────────────────────────────────────────────────────
# Applied against lowercased body text.  Each entry maps to exactly one chapter
# ID.  All matching keywords fire; keeping multiple IDs from one unit is correct
# for braided exercises ("Functions" spanning ln + exp → {6, 7}).

_KEYWORD_MAP: dict[str, int] = {
    # ── Ch 1: Parallelism and Orthogonality in Space ──────────────────────────
    "relative position of two planes": 1,
    "relative position of a line and a plane": 1,
    "relative position of two lines": 1,
    "parametric equation of": 1,
    "perpendicular plane": 1,
    "parallel plane": 1,
    "distance from a point to a plane": 1,
    "distance from a point to a line": 1,
    "orthogonality of": 1,
    "space is referred to": 1,
    "space referred to": 1,
    # ── Ch 2: Continuous Functions on an Interval ─────────────────────────────
    "intermediate value theorem": 2,
    "intermediate value": 2,
    "continuous on the interval": 2,
    "continuous on [": 2,
    "root of the equation": 2,
    "extending by continuity": 2,
    "by continuity": 2,
    "image of a closed interval": 2,
    # ── Ch 3: Inverse Functions ───────────────────────────────────────────────
    "f⁻¹": 3,
    "f^{-1}": 3,
    "bijective": 3,
    "inverse of f": 3,
    "composition of f and g": 3,
    # ── Ch 4: Inverse Trigonometric Functions ─────────────────────────────────
    "arcsin": 4,
    "arccos": 4,
    "arctan": 4,
    "arc sin": 4,
    "arc cos": 4,
    "arc tan": 4,
    # ── Ch 5: Differential Calculus / L'Hôpital ──────────────────────────────
    "l'hôpital": 5,
    "l'hopital": 5,
    "lhôpital": 5,
    "lhopital": 5,
    "rolle's theorem": 5,
    "rolle theorem": 5,
    "mean value theorem": 5,
    # ── Ch 6: Natural Logarithm ───────────────────────────────────────────────
    "logarith": 6,
    "natural log": 6,
    "\\ln": 6,
    "ln(": 6,
    "ln ": 6,
    # ── Ch 7: Exponential Function ────────────────────────────────────────────
    "exponential": 7,
    "e^{": 7,
    "e^{-": 7,
    "e^x": 7,
    "e^(": 7,
    "e−x": 7,
    "exp(": 7,
    # ── Ch 8: Second and Higher Order Derivatives ─────────────────────────────
    "second derivative": 8,
    "f''": 8,
    "f ′′": 8,
    "concave upward": 8,
    "concave downward": 8,
    "concave up": 8,
    "concave down": 8,
    "inflection point": 8,
    "point of inflection": 8,
    "concavity": 8,
    # ── Ch 9: Numerical Sequences ─────────────────────────────────────────────
    "u_{n": 9,
    "u_n": 9,
    "(u_n)": 9,
    "u(n)": 9,
    "arithmetic sequence": 9,
    "geometric sequence": 9,
    "bounded sequence": 9,
    "limit of a sequence": 9,
    "convergent sequence": 9,
    "consider the sequence": 9,
    # ── Ch 10: Definite Integral — Definition and Properties ──────────────────
    "linearity of the integral": 10,
    "from integral to antiderivative": 10,
    "inequalities and integrals": 10,
    # ── Ch 11: Integration — Substitution / Even-Odd ─────────────────────────
    "change of variable": 11,
    "integration by substitution": 11,
    "even function": 11,
    "odd function": 11,
    # ── Ch 12: Integration — By Parts / Rational Fractions ───────────────────
    "by parts": 12,
    "rational fraction": 12,
    "partial fraction": 12,
    # ── Ch 13: Applications of Integration — Area ─────────────────────────────
    "area between": 13,
    "area bounded": 13,
    "area of the region": 13,
    "area of d": 13,
    "area enclosed": 13,
    "bounded by the curves": 13,
    "bounded by the curve": 13,
    "calculate the area": 13,
    # ── Ch 14: First Order ODE ────────────────────────────────────────────────
    # "y' -" and "y' +" catch the standard ODE forms "y' - ay = f(x)" and
    # "y' + ay = f(x)" where the equality is not directly adjacent to "y'".
    "y' =": 14,
    "y'=": 14,
    "y' -": 14,
    "y' +": 14,
    "separable equation": 14,
    "separable differential": 14,
    "first order linear": 14,
    "dy/dx": 14,
    # ── Ch 15: Second Order ODE ───────────────────────────────────────────────
    "y''": 15,
    "reduced equation": 15,
    "characteristic equation": 15,
    "second order linear": 15,
    "ω²y": 15,
    # ── Ch 16: Combinations ───────────────────────────────────────────────────
    "pascal's triangle": 16,
    "pascal triangle": 16,
    "binomial formula": 16,
    "binomial theorem": 16,
    "c(n,": 16,
    "c_n^": 16,
    # ── Ch 17: Conditional Probability ───────────────────────────────────────
    "conditional probability": 17,
    "independent events": 17,
    "total probability": 17,
    "rule of total probability": 17,
    "p(a|b)": 17,
    "p(a/b)": 17,
    "bayes": 17,
    "an urn": 17,
    "two urns": 17,
    "a bag": 17,
    "contains cards": 17,
    "fair die": 17,
    # ── Ch 18: Random Variables ───────────────────────────────────────────────
    "random variable": 18,
    "probability distribution": 18,
    "distribution function": 18,
    "expected value": 18,
    "variance": 18,
    "standard deviation": 18,
    "e(x) =": 18,
    "v(x) =": 18,
    "σ²": 18,
}


# ── Taxonomy ───────────────────────────────────────────────────────────────────


def load_taxonomy(path: Path = _CURRICULUM_PATH) -> dict[int, str]:
    """Return {chapter_id: title} from curriculum.json. Chapter 0 = OTHER."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    taxonomy: dict[int, str] = {0: "OTHER (out of scope / pre-reform)"}
    for entry in raw["topics"]:
        taxonomy[entry["chapter"]] = entry["title"]
    return taxonomy


# ── Core tagger ────────────────────────────────────────────────────────────────


def match_header(normalized: str) -> set[int]:
    """Return chapter IDs for a normalized header via exact dict lookup."""
    return set(_HEADER_MAP.get(normalized, set()))


def scan_keywords(text: str) -> set[int]:
    """Return the set of chapter IDs whose keywords appear in body text."""
    lower = text.lower()
    return {ch_id for kw, ch_id in _KEYWORD_MAP.items() if kw in lower}


def resolve_chapters(
    header_ids: set[int], keyword_ids: set[int]
) -> tuple[list[int], str]:
    """Combine header and keyword evidence into final chapter IDs.

    Resolution rules (per spec):
    - Single header id + body agrees or silent → {header id}  (header wins)
    - Ambiguous header set + body keywords → intersect; if empty, take body-fired
    - No header match + body keywords → {body keyword ids}
    - Nothing fired → {0}  (OTHER)
    """
    if not header_ids and not keyword_ids:
        return [0], "none"

    if len(header_ids) == 1:
        return sorted(header_ids), "header"

    if not header_ids:
        return sorted(keyword_ids), "keyword"

    # Ambiguous header — intersect with keyword evidence.
    intersect = header_ids & keyword_ids
    if intersect:
        return sorted(intersect), "both"
    if keyword_ids:
        return sorted(keyword_ids), "both"
    # No keyword evidence at all — return the full ambiguous set as-is.
    return sorted(header_ids), "header"


def chunks_to_units(chunks: list[dict]) -> list[dict]:
    """Convert chunker output to tagger input.

    Each chunk's first line is the raw exercise header (e.g. "II - Natural
    Logarithm (4 points)"); the full content is used as the keyword-pass body.
    Only source_type='past_exam' chunks are included — answer_key chunks are
    solutions, not questions, and must not be tagged or counted.
    """
    units: list[dict] = []
    for chunk in chunks:
        if chunk.get("source_type") != "past_exam":
            continue
        content = chunk.get("content", "")
        header = content.split("\n")[0].strip() if content else ""
        units.append(
            {
                "exam_id": f"{chunk['year']}_s{chunk['session']}",
                "year": chunk["year"],
                "session": chunk["session"],
                "exercise_id": chunk["exercise_id"],
                "header": header,
                "text": content,
            }
        )
    return units


def tag_unit(unit: dict) -> dict:
    """Tag one exercise unit; return a new dict with chapter_ids and matched_via."""
    normalized = normalize_header(unit.get("header", ""))
    header_ids = match_header(normalized)
    keyword_ids = scan_keywords(unit.get("text", ""))

    chapter_ids, matched_via = resolve_chapters(header_ids, keyword_ids)

    return {
        "exam_id": unit.get("exam_id"),
        "year": unit["year"],
        "session": unit["session"],
        "exercise_id": unit["exercise_id"],
        "header": unit.get("header", ""),
        "chapter_ids": chapter_ids,
        "matched_via": matched_via,
    }


def tag_all_units(units: list[dict]) -> list[dict]:
    """Tag every exercise unit deterministically."""
    tags: list[dict] = []
    for unit in units:
        tags.append(tag_unit(unit))
    logger.info("Tagged %d units", len(tags))
    return tags


# ── Output helpers ─────────────────────────────────────────────────────────────


def write_tags(tags: list[dict], output_path: Path) -> None:
    """Write tagged units to JSON (ground truth; overwrites on each run)."""
    output_path.write_text(
        json.dumps(tags, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Wrote %d tagged units → %s", len(tags), output_path)


# ── Aggregation ────────────────────────────────────────────────────────────────


async def fetch_chunks_from_db(db_url: str) -> list[dict]:
    """Return all past_exam chunks from the chunks table as plain dicts."""
    pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(pg_url)
    try:
        rows = await conn.fetch(
            """
            SELECT year, session, exercise_id, content
            FROM chunks
            WHERE source_type = 'past_exam'
            ORDER BY year, session, exercise_id
            """
        )
        return [
            {
                "source_type": "past_exam",
                "year": row["year"],
                "session": row["session"],
                "exercise_id": row["exercise_id"],
                "content": row["content"],
            }
            for row in rows
        ]
    finally:
        await conn.close()


# ── Coverage report ────────────────────────────────────────────────────────────


def print_coverage_report(tags: list[dict], taxonomy: dict[int, str]) -> None:
    """Print a human-readable coverage summary to stdout."""
    counts: dict[str, int] = {"header": 0, "keyword": 0, "both": 0, "none": 0}
    none_units: list[dict] = []

    for tag in tags:
        via = tag["matched_via"]
        counts[via] = counts.get(via, 0) + 1
        if via == "none":
            none_units.append(tag)

    total = len(tags)
    pct = lambda n: f"{n / total * 100:.1f}%" if total else "0%"

    print(f"\n{'=' * 50}")
    print(f"Coverage Report  ({total} units)")
    print(f"{'=' * 50}")
    print(f"  header:  {counts['header']:>4}  ({pct(counts['header'])})")
    print(f"  keyword: {counts['keyword']:>4}  ({pct(counts['keyword'])})")
    print(f"  both:    {counts['both']:>4}  ({pct(counts['both'])})")
    print(f"  none:    {counts['none']:>4}  ({pct(counts['none'])})")
    print()

    if none_units:
        print(f"Unresolved units — extend _HEADER_MAP or _KEYWORD_MAP:")
        for u in none_units:
            print(
                f"  [{u['year']} S{u['session']} Ex{u['exercise_id']}]"
                f"  header={u['header']!r}"
            )
    else:
        print("All units resolved — no 'none' entries.")

    # Chapter appearance summary
    ch_counts: dict[int, int] = defaultdict(int)
    for tag in tags:
        for ch_id in tag["chapter_ids"]:
            ch_counts[ch_id] += 1

    print(f"\nChapter distribution (unit counts, including multi-tagged):")
    for ch_id in sorted(ch_counts):
        title = taxonomy.get(ch_id, f"Chapter {ch_id}")
        print(f"  [{ch_id:>2}] {title:<50}  {ch_counts[ch_id]:>3} units")


# ── CLI entry point ────────────────────────────────────────────────────────────


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[topic_tagging] %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Deterministic topic tagging for Lebanese GS exam chunks"
    )
    parser.add_argument(
        "--chunks-file",
        default="",
        help=(
            "Path to a chunks JSON file produced by the extraction pipeline "
            "(e.g. .ingestion_cache/01_chunks.json). "
            "If omitted, chunks are read from the DB via --db-url."
        ),
    )
    parser.add_argument(
        "--output",
        default=str(_DEFAULT_OUTPUT),
        help="Output path for question_tags.json (default: app/data/question_tags.json)",
    )
    parser.add_argument(
        "--db-url",
        default="postgresql://postgres:devpassword@localhost:5432/lebanese_math",
        help="PostgreSQL connection URL (used to read chunks and upsert topic_stats).",
    )
    args = parser.parse_args()

    if args.chunks_file:
        chunks_path = Path(args.chunks_file)
        if not chunks_path.exists():
            raise SystemExit(f"Chunks file not found: {chunks_path}")
        try:
            chunks: list[dict] = json.loads(chunks_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Failed to parse chunks file: {exc}") from exc
        if not isinstance(chunks, list):
            raise SystemExit("Chunks file must contain a JSON array at the top level.")
        logger.info("Loaded %d chunks from %s", len(chunks), chunks_path)
    else:
        if not args.db_url:
            raise SystemExit(
                "Provide either --chunks-file or --db-url to read chunks from the database."
            )
        logger.info("Fetching past_exam chunks from database...")
        chunks = asyncio.run(fetch_chunks_from_db(args.db_url))
        logger.info("Fetched %d chunks from DB", len(chunks))

    units = chunks_to_units(chunks)
    logger.info(
        "Converted to %d past_exam units (skipped %d non-question chunks)",
        len(units),
        len(chunks) - len(units),
    )

    taxonomy = load_taxonomy()
    tags = tag_all_units(units)

    output_path = Path(args.output)
    write_tags(tags, output_path)

    print_coverage_report(tags, taxonomy)


if __name__ == "__main__":
    main()
