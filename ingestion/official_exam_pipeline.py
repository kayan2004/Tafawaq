"""Official exam ingestion pipeline: PDF → Claude extraction → PostgreSQL + MinIO.

Extracts full exercise content (with LaTeX) from each PDF using Claude.
Grading at exam-time also uses the PDF (official solutions).

Usage:
    # First run — inserts new rows:
    uv run python -m ingestion.official_exam_pipeline \\
        --anthropic-key sk-ant-... \\
        [--pdf-dir /path/to/pdfs]

    # Update existing rows with extracted content:
    uv run python -m ingestion.official_exam_pipeline \\
        --anthropic-key sk-ant-... \\
        --update \\
        [--pdf-dir /path/to/pdfs]

Each PDF is processed one at a time (sequential, not parallel).
"""
import argparse
import asyncio
import json
import os
import re
import uuid
from pathlib import Path

import asyncpg

from prompts.math.official_exam_parsing import EXTRACTION_SYSTEM_PROMPT as _EXTRACTION_SYSTEM

_REPO_ROOT = Path(__file__).parent.parent
_BUCKET = "past-exams"
_MODEL = "claude-sonnet-4-5"

# Stable UUID namespace — never change.
_OFFICIAL_EXAM_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def _exam_uuid(year: int, session_label: str) -> str:
    return str(uuid.uuid5(_OFFICIAL_EXAM_NS, f"{year}:{session_label}"))


def _parse_filename(filename: str) -> tuple[int, str] | None:
    m = re.search(r"(\d{4})_(Session\d+|Regular|Exceptional)", filename, re.IGNORECASE)
    if not m:
        return None
    year = int(m.group(1))
    raw = m.group(2)
    session_label = re.sub(r"(?i)(session)(\d+)", r"Session \2", raw)
    return year, session_label


def _extract_with_claude(pdf_path: Path, pdf_key: str, api_key: str) -> tuple[dict, dict, list[str]]:
    """Send the PDF to Claude and extract both questions and answer key.

    Returns (exam_content, answer_key, warnings).
    """
    import base64
    import anthropic

    pdf_bytes = pdf_path.read_bytes()
    b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_MODEL,
        max_tokens=16384,
        system=_EXTRACTION_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract the English question section into exam_content and "
                            "the English answer key section into answer_key. Return JSON only."
                        ),
                    },
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.rstrip())

    parsed = json.loads(raw)
    exam_content = parsed.get("exam_content", {})
    answer_key = parsed.get("answer_key", {})

    exercises = exam_content.get("exercises", [])
    warnings: list[str] = []
    if not exercises:
        warnings.append("Claude returned no exercises")
    else:
        total = round(sum(e.get("total_marks", 0) for e in exercises), 2)
        if abs(total - 20.0) > 0.5 and abs(total - 28.0) > 0.5:
            warnings.append(f"Total marks = {total} (expected ~20 or ~28)")

    if not answer_key.get("exercises"):
        warnings.append("No answer key exercises extracted")

    return exam_content, answer_key, warnings


async def _insert_exam(
    conn: asyncpg.Connection,
    exam_id: str,
    year: int,
    session_label: str,
    exam_content: dict,
    answer_key: dict,
    pdf_key: str,
) -> bool:
    """Insert new exam row (skip if already exists). Returns True if inserted."""
    result = await conn.fetchval(
        """
        INSERT INTO official_exams (id, year, session_label, exam_content, answer_key, pdf_key)
        VALUES ($1::uuid, $2, $3, $4::jsonb, $5::jsonb, $6)
        ON CONFLICT ON CONSTRAINT uq_official_exams_year_session DO NOTHING
        RETURNING id
        """,
        exam_id,
        year,
        session_label,
        json.dumps(exam_content),
        json.dumps(answer_key),
        pdf_key,
    )
    return result is not None


async def _update_exam_content(
    conn: asyncpg.Connection,
    year: int,
    session_label: str,
    exam_content: dict,
    answer_key: dict,
) -> bool:
    """Update exam_content and answer_key for an existing row. Returns True if the row existed."""
    result = await conn.fetchval(
        """
        UPDATE official_exams
        SET exam_content = $1::jsonb, answer_key = $2::jsonb
        WHERE year = $3 AND session_label = $4
        RETURNING id
        """,
        json.dumps(exam_content),
        json.dumps(answer_key),
        year,
        session_label,
    )
    return result is not None


def _upload_pdf(endpoint: str, access_key: str, secret_key: str, pdf_key: str, data: bytes) -> None:
    try:
        import io
        from minio import Minio
        client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        if not client.bucket_exists(_BUCKET):
            client.make_bucket(_BUCKET)
        client.put_object(_BUCKET, pdf_key, io.BytesIO(data), length=len(data))
    except Exception as exc:
        print(f"  [minio] WARNING: upload failed — {exc}")


async def run_pipeline(
    pdf_dir: str,
    db_url: str,
    minio_endpoint: str,
    minio_access_key: str,
    minio_secret_key: str,
    anthropic_key: str,
    update: bool = False,
) -> None:
    pdf_path = Path(pdf_dir)
    pdf_files = sorted(pdf_path.glob("*.pdf"))

    print(f"[official] Scanning: {pdf_path.resolve()}")

    if not pdf_files:
        print(f"[official] No PDF files found in {pdf_dir}")
        return

    print(f"[official] Found {len(pdf_files)} PDF file(s)  mode={'UPDATE' if update else 'INSERT'}")

    db_url_asyncpg = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url_asyncpg)

    inserted = 0
    updated = 0
    skipped = 0
    failed: list[str] = []

    try:
        for pdf_file in pdf_files:
            parsed = _parse_filename(pdf_file.name)
            if not parsed:
                print(f"[official] SKIP {pdf_file.name} — cannot parse year/session from filename")
                skipped += 1
                continue

            year, session_label = parsed
            exam_id = _exam_uuid(year, session_label)
            pdf_key = f"{year}_{session_label.replace(' ', '_')}.pdf"

            print(f"[official] Processing {pdf_file.name} -> {year} {session_label} ...")

            try:
                pdf_bytes = pdf_file.read_bytes()
                exam_content, answer_key, warnings = _extract_with_claude(pdf_file, pdf_key, anthropic_key)

                for w in warnings:
                    print(f"  WARNING: {w}")

                if not exam_content.get("exercises"):
                    print("  SKIP — no exercises extracted")
                    failed.append(pdf_file.name)
                    continue

                ex_count = len(exam_content["exercises"])
                total = sum(e.get("total_marks", 0) for e in exam_content["exercises"])
                ak_count = len(answer_key.get("exercises", []))
                print(f"  Extracted: {ex_count} exercises, {total:.1f} total marks, {ak_count} answer key exercises")

                if update:
                    was_found = await _update_exam_content(conn, year, session_label, exam_content, answer_key)
                    if was_found:
                        print(f"  OK — updated (year={year} session={session_label})")
                        updated += 1
                    else:
                        # Row doesn't exist yet — insert it.
                        was_inserted = await _insert_exam(
                            conn, exam_id, year, session_label, exam_content, answer_key, pdf_key
                        )
                        if was_inserted:
                            _upload_pdf(minio_endpoint, minio_access_key, minio_secret_key, pdf_key, pdf_bytes)
                            print(f"  OK — inserted (id={exam_id})")
                            inserted += 1
                        else:
                            print("  ERROR — update and insert both failed")
                            failed.append(pdf_file.name)
                else:
                    was_inserted = await _insert_exam(
                        conn, exam_id, year, session_label, exam_content, answer_key, pdf_key
                    )
                    if was_inserted:
                        _upload_pdf(minio_endpoint, minio_access_key, minio_secret_key, pdf_key, pdf_bytes)
                        print(f"  OK — inserted (id={exam_id})")
                        inserted += 1
                    else:
                        print(f"  SKIP — already in database (use --update to overwrite)")
                        skipped += 1

            except Exception as exc:
                print(f"  ERROR — {exc}")
                failed.append(pdf_file.name)

    finally:
        await conn.close()

    print(f"\n[official] Done: {inserted} inserted, {updated} updated, {skipped} skipped, {len(failed)} failed")
    if failed:
        print("[official] Failed files:")
        for f in failed:
            print(f"  - {f}")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Lebanese Math Coach official exam ingestion")
    parser.add_argument(
        "--pdf-dir",
        default=os.getenv("PDF_DIR", str(_REPO_ROOT / "Math_GS_Exams_English")),
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:devpassword@localhost:5432/lebanese_math",
        ),
    )
    parser.add_argument("--minio-endpoint", default=os.getenv("MINIO_ENDPOINT", "localhost:9000"))
    parser.add_argument("--minio-access-key", default=os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
    parser.add_argument("--minio-secret-key", default=os.getenv("MINIO_SECRET_KEY", "minioadmin"))
    parser.add_argument("--anthropic-key", default=os.getenv("ANTHROPIC_API_KEY", ""), required=False)
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update exam_content for rows already in the database (default: skip existing)",
    )
    args = parser.parse_args()

    if not args.anthropic_key:
        raise SystemExit("ERROR: --anthropic-key is required (or set ANTHROPIC_API_KEY env var)")

    asyncio.run(
        run_pipeline(
            pdf_dir=args.pdf_dir,
            db_url=args.db_url,
            minio_endpoint=args.minio_endpoint,
            minio_access_key=args.minio_access_key,
            minio_secret_key=args.minio_secret_key,
            anthropic_key=args.anthropic_key,
            update=args.update,
        )
    )
