"""Ingest Building Up Mathematics textbooks into textbook_pages.

Reads either:
  - a ===PAGE N=== / ===END PAGE N=== markdown file (--file), or
  - a PDF directly (--pdf), extracting text with pdfplumber.

Usage:
    # From existing markdown:
    uv run python -m ingestion.book_ingest \
        --file textbook/building_up_mathematics_1.md

    # Directly from PDF (book 2, offset pages by 300 to avoid DB conflicts):
    uv run python -m ingestion.book_ingest \
        --pdf "Building up Mathematics Calculus and Statistics - Pages 1-251.PDF" \
        --chapter "Building Up Mathematics — Calculus and Statistics" \
        --page-offset 300 \
        --save-md textbook/building_up_mathematics_2.md
"""
from __future__ import annotations

import argparse
import asyncio
import io
import os
import re
import uuid
from pathlib import Path

import asyncpg

_DEFAULT_DB = "postgresql://postgres:devpassword@localhost:5432/lebanese_math"
_DEFAULT_CHAPTER = "Building Up Mathematics — Algebra and Geometry"

# Pages this short (after stripping) are blank/noise — skip them.
_MIN_CONTENT_LEN = 20


def _parse_pages(text: str) -> list[tuple[int, str]]:
    pattern = re.compile(r"===PAGE (\d+)===\n(.*?)===END PAGE \1===", re.DOTALL)
    pages = []
    for m in pattern.finditer(text):
        page_number = int(m.group(1))
        content = m.group(2).strip()
        if len(content) >= _MIN_CONTENT_LEN:
            pages.append((page_number, content))
    return pages


def _extract_from_pdf(pdf_path: str, page_offset: int) -> list[tuple[int, str]]:
    import pdfplumber

    pdf_bytes = Path(pdf_path).read_bytes()
    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text and len(text.strip()) >= _MIN_CONTENT_LEN:
                pages.append((i + page_offset, text.strip()))
    return pages


def _pages_to_md(pages: list[tuple[int, str]]) -> str:
    lines = []
    for page_num, content in pages:
        lines.append(f"===PAGE {page_num}===")
        lines.append(content)
        lines.append(f"===END PAGE {page_num}===")
        lines.append("")
    return "\n".join(lines)


async def run(pages: list[tuple[int, str]], chapter: str, db_url: str) -> None:
    if not pages:
        print("[book_ingest] No pages found — check the file format.")
        return

    print(f"[book_ingest] Parsed {len(pages)} non-blank pages.")

    conn = await asyncpg.connect(db_url)
    try:
        rows = [
            (str(uuid.uuid4()), page_num, chapter, "", "theory", content)
            for page_num, content in pages
        ]
        await conn.executemany(
            """
            INSERT INTO textbook_pages
              (id, page_number, chapter, section, page_type, content)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (page_number) DO UPDATE
              SET content = EXCLUDED.content,
                  chapter = EXCLUDED.chapter
            """,
            rows,
        )
        print(f"[book_ingest] Upserted {len(rows)} rows into textbook_pages.")
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Building Up Mathematics textbook")
    parser.add_argument("--file", default=None, help="Path to ===PAGE N=== formatted markdown")
    parser.add_argument("--pdf", default=None, help="Path to PDF — extracts text directly")
    parser.add_argument("--chapter", default=_DEFAULT_CHAPTER)
    parser.add_argument("--page-offset", type=int, default=0,
                        help="Add this to every PDF page number before storing (use to avoid conflicts)")
    parser.add_argument("--save-md", default=None,
                        help="If set, write extracted pages as ===PAGE N=== markdown to this path")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", _DEFAULT_DB))
    args = parser.parse_args()

    if args.pdf:
        pages = _extract_from_pdf(args.pdf, args.page_offset)
        if args.save_md:
            Path(args.save_md).write_text(_pages_to_md(pages), encoding="utf-8")
            print(f"[book_ingest] Saved markdown to {args.save_md}")
    elif args.file:
        text = Path(args.file).read_text(encoding="utf-8")
        pages = _parse_pages(text)
    else:
        parser.error("Provide either --file or --pdf")

    asyncio.run(run(pages, args.chapter, args.db_url))
