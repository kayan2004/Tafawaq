"""Offline textbook ingestion pipeline: markdown pages → textbook_pages."""
import argparse
import asyncio
import os
import uuid
from pathlib import Path
from typing import Any

import asyncpg
import yaml


class SkipFile(Exception):
    pass


# ── Parsing ───────────────────────────────────────────────────────────────────


def _parse_block(block: str, source: str = "") -> dict[str, Any]:
    """Parse one YAML-frontmatter page block (text between PAGE_BREAK separators).

    Raises SkipFile on missing/malformed fields or non-integer page value.
    """
    parts = block.strip().split("---", 2)
    if len(parts) < 3:
        raise SkipFile(f"Missing frontmatter delimiters in block from {source}")

    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        raise SkipFile(f"YAML error in {source}: {exc}")

    if not isinstance(meta, dict):
        raise SkipFile(f"Frontmatter is not a mapping in {source}")

    for field in ("page", "chapter", "section", "type"):
        if field not in meta:
            raise SkipFile(f"Missing required field '{field}' in {source}")

    try:
        page_number = int(meta["page"])
    except (ValueError, TypeError):
        raise SkipFile(f"Non-integer page value '{meta['page']}' in {source}")

    return {
        "page_number": page_number,
        "chapter": str(meta["chapter"]),
        "section": str(meta["section"]),
        "page_type": str(meta["type"]),
        "content": parts[2].strip(),
    }


def parse_page(path: Path) -> list[dict[str, Any]]:
    """Read a multi-page markdown file and return all valid page dicts.

    Pages are separated by ===PAGE_BREAK=== within each file. Blocks with
    non-integer page values or malformed frontmatter are skipped with a warning.
    Raises SkipFile if the file cannot be read at all.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SkipFile(f"Cannot read {path}: {exc}")

    pages: list[dict[str, Any]] = []
    for block in raw.split("===PAGE_BREAK==="):
        block = block.strip()
        if not block:
            continue
        try:
            pages.append(_parse_block(block, source=str(path)))
        except SkipFile as exc:
            print(f"[textbook] WARNING: {exc}")

    return pages


# ── Insert (also used by app/services/admin_service.py) ───────────────────────


async def insert_textbook_pages(conn, pages: list[dict[str, Any]]) -> int:
    """Upsert textbook_pages rows. Returns the number of rows inserted."""
    page_rows = [
        (
            str(uuid.uuid4()),
            p["page_number"],
            p["chapter"],
            p["section"],
            p["page_type"],
            p["content"],
        )
        for p in pages
    ]
    await conn.executemany(
        """
        INSERT INTO textbook_pages
          (id, page_number, chapter, section, page_type, content)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (page_number) DO NOTHING
        """,
        page_rows,
    )
    return len(page_rows)


# ── Pipeline ──────────────────────────────────────────────────────────────────


async def run_pipeline(textbook_dir: str, db_url: str) -> None:
    db_url_asyncpg = db_url.replace("postgresql+asyncpg://", "postgresql://")
    textbook_path = Path(textbook_dir)
    md_files = sorted(textbook_path.glob("*.md"))

    if not md_files:
        print(f"[textbook] No .md files found in {textbook_dir}")
        return

    all_pages: list[dict] = []
    skipped_files: list[str] = []

    print(f"[textbook] Parsing {len(md_files)} file(s)...")
    for md_file in md_files:
        try:
            pages = parse_page(md_file)
            if not pages:
                print(f"[textbook] WARNING: no valid pages in {md_file.name}")
                skipped_files.append(str(md_file))
                continue
            all_pages.extend(pages)
            print(f"[textbook] {md_file.name}: {len(pages)} pages")
        except SkipFile as exc:
            print(f"[textbook] WARNING: skipping {md_file.name} - {exc}")
            skipped_files.append(str(md_file))

    if not all_pages:
        print("[textbook] No pages parsed - aborting")
        return

    print("[textbook] Inserting into PostgreSQL...")
    conn = await asyncpg.connect(db_url_asyncpg)
    try:
        page_count = await insert_textbook_pages(conn, all_pages)
        print(f"[textbook] Upserted {page_count} textbook_pages rows")
    finally:
        await conn.close()

    if skipped_files:
        print(f"\n[textbook] Skipped {len(skipped_files)} file(s):")
        for f in skipped_files:
            print(f"  - {f}")
    else:
        print("[textbook] Complete — no files skipped")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(
        description="Lebanese Math Coach textbook ingestion pipeline"
    )
    parser.add_argument(
        "--textbook-dir",
        default=os.getenv("TEXTBOOK_DIR", "textbook"),
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:devpassword@localhost:5432/lebanese_math",
        ),
    )
    args = parser.parse_args()

    asyncio.run(run_pipeline(textbook_dir=args.textbook_dir, db_url=args.db_url))
