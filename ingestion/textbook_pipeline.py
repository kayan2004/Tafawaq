"""Offline textbook ingestion pipeline: markdown pages → pgvector chunks."""
import argparse
import asyncio
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

import anthropic
import asyncpg
import pgvector.asyncpg
import voyageai
import yaml

# Textbook-specific UUID namespace — stable, never change.
_TEXTBOOK_NS = uuid.NAMESPACE_OID

_SOURCE_TYPE_MAP = {
    "theory": "textbook_theory",
    "exercise": "textbook_exercise",
    "self_evaluation": "textbook_self_evaluation",
    "mixed": "textbook_theory",
}

_SKIP_TYPES = {"blank", "preface", "just_for_fun"}

from prompts.math.tagging_textbook import TAG_PROMPT as _TAG_PROMPT


class SkipFile(Exception):
    pass


# ── Chunk UUID ────────────────────────────────────────────────────────────────


def _chunk_uuid(source_type: str, page_start: int, page_end: int) -> str:
    return str(uuid.uuid5(_TEXTBOOK_NS, f"{source_type}:{page_start}:{page_end}"))


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


# ── Chunking ──────────────────────────────────────────────────────────────────


def chunk_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group consecutive pages by (chapter, section) into chunks.

    Pages with page_type in {blank, preface, just_for_fun} are excluded.
    Page type 'mixed' maps to source_type 'textbook_theory'.
    """
    eligible = sorted(
        [p for p in pages if p["page_type"] not in _SKIP_TYPES],
        key=lambda p: p["page_number"],
    )
    chunks: list[dict[str, Any]] = []
    i = 0
    while i < len(eligible):
        page = eligible[i]
        source_type = _SOURCE_TYPE_MAP.get(page["page_type"])
        if source_type is None:
            i += 1
            continue

        key = (page["chapter"], page["section"])
        group = [page]
        j = i + 1
        while j < len(eligible) and (
            eligible[j]["chapter"],
            eligible[j]["section"],
        ) == key:
            group.append(eligible[j])
            j += 1

        chunks.append({
            "source_type": source_type,
            "chapter": page["chapter"],
            "section": page["section"],
            "page_start": min(p["page_number"] for p in group),
            "page_end": max(p["page_number"] for p in group),
            "content": "\n\n".join(p["content"] for p in group),
            "topic": "",
            "subtopic": "",
        })
        i = j

    return chunks


# ── Tagging ───────────────────────────────────────────────────────────────────


def tag_chunks(chunks: list[dict], api_key: str) -> list[dict]:
    """Tag each chunk with topic/subtopic via claude-haiku.

    On failure, keeps the chunk with topic='Unknown' and logs a warning.
    """
    client = anthropic.Anthropic(api_key=api_key)
    for chunk in chunks:
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=128,
                messages=[
                    {
                        "role": "user",
                        "content": _TAG_PROMPT.format(content=chunk["content"][:800]),
                    }
                ],
            )
            raw = response.content[0].text
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(match.group() if match else raw)
            chunk["topic"] = str(data.get("topic", "Unknown"))
            chunk["subtopic"] = str(data.get("subtopic", ""))
        except (json.JSONDecodeError, KeyError, IndexError, anthropic.APIError) as exc:
            print(
                f"[textbook] WARNING: tagging failed"
                f" ({chunk.get('section', '?')}) - {exc}"
            )
            chunk["topic"] = "Unknown"
            chunk["subtopic"] = ""
    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────


async def embed_chunks(chunks: list[dict], api_key: str) -> list[dict]:
    """Embed chunk content via voyage-large-2 in batches of 16.

    Uses asyncio.to_thread to avoid blocking the event loop.
    """
    client = voyageai.Client(api_key=api_key)
    batch_size = 16
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        result = await asyncio.to_thread(
            client.embed,
            [c["content"] for c in batch],
            model="voyage-large-2",
            input_type="document",
        )
        for j, chunk in enumerate(batch):
            chunk["embedding"] = result.embeddings[j]
    return chunks


# ── Pipeline ──────────────────────────────────────────────────────────────────


async def run_pipeline(
    textbook_dir: str,
    db_url: str,
    anthropic_key: str,
    voyage_key: str,
) -> None:
    db_url_asyncpg = db_url.replace("postgresql+asyncpg://", "postgresql://")
    textbook_path = Path(textbook_dir)
    md_files = sorted(textbook_path.glob("*.md"))

    if not md_files:
        print(f"[textbook] No .md files found in {textbook_dir}")
        return

    all_pages: list[dict] = []
    all_chunks: list[dict] = []
    skipped_files: list[str] = []

    # ── Stage 1: Parse ────────────────────────────────────────────────────────
    print(f"[textbook] Parsing {len(md_files)} file(s)...")
    for md_file in md_files:
        try:
            pages = parse_page(md_file)
            if not pages:
                print(f"[textbook] WARNING: no valid pages in {md_file.name}")
                skipped_files.append(str(md_file))
                continue
            chunks = chunk_pages(pages)
            all_pages.extend(pages)
            all_chunks.extend(chunks)
            print(
                f"[textbook] {md_file.name}: {len(pages)} pages,"
                f" {len(chunks)} chunks"
            )
        except SkipFile as exc:
            print(f"[textbook] WARNING: skipping {md_file.name} - {exc}")
            skipped_files.append(str(md_file))

    if not all_pages:
        print("[textbook] No pages parsed - aborting")
        return

    # ── Stage 2: Tag ──────────────────────────────────────────────────────────
    if all_chunks:
        print(f"[textbook] Tagging {len(all_chunks)} chunks via claude-haiku...")
        all_chunks = await asyncio.to_thread(tag_chunks, all_chunks, anthropic_key)

    # ── Stage 3: Embed ────────────────────────────────────────────────────────
    if all_chunks:
        print(f"[textbook] Embedding {len(all_chunks)} chunks via voyage-large-2...")
        all_chunks = await embed_chunks(all_chunks, voyage_key)

    # ── Stage 4: Insert into PostgreSQL ───────────────────────────────────────
    print("[textbook] Inserting into pgvector...")
    conn = await asyncpg.connect(db_url_asyncpg)
    await pgvector.asyncpg.register_vector(conn)

    try:
        page_rows = [
            (
                str(uuid.uuid4()),
                p["page_number"],
                p["chapter"],
                p["section"],
                p["page_type"],
                p["content"],
            )
            for p in all_pages
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
        print(f"[textbook] Upserted {len(page_rows)} textbook_pages rows")

        chunk_rows = [
            (
                _chunk_uuid(c["source_type"], c["page_start"], c["page_end"]),
                c["source_type"],
                c["topic"],
                c["subtopic"],
                c["content"],
                c["embedding"],
                c["page_start"],
                c["page_end"],
            )
            for c in all_chunks
            if "embedding" in c
        ]
        if chunk_rows:
            await conn.executemany(
                """
                INSERT INTO chunks
                  (id, source_type, topic, subtopic, content, embedding,
                   page_start, page_end)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO NOTHING
                """,
                chunk_rows,
            )
            print(f"[textbook] Inserted {len(chunk_rows)} chunk rows")
    finally:
        await conn.close()

    # ── Summary ────────────────────────────────────────────────────────────────
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
    parser.add_argument(
        "--anthropic-key",
        default=os.getenv("ANTHROPIC_API_KEY", ""),
    )
    parser.add_argument(
        "--voyage-key",
        default=os.getenv("VOYAGE_API_KEY", ""),
    )
    args = parser.parse_args()

    if not args.anthropic_key:
        raise SystemExit(
            "Missing ANTHROPIC_API_KEY (pass via --anthropic-key or env var)"
        )
    if not args.voyage_key:
        raise SystemExit(
            "Missing VOYAGE_API_KEY (pass via --voyage-key or env var)"
        )

    asyncio.run(
        run_pipeline(
            textbook_dir=args.textbook_dir,
            db_url=args.db_url,
            anthropic_key=args.anthropic_key,
            voyage_key=args.voyage_key,
        )
    )
