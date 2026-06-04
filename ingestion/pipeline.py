"""Offline ingestion pipeline: MinIO PDFs → pgvector chunks."""
import argparse
import asyncio
import json
import os
import re
import shutil
import uuid
from io import BytesIO
from pathlib import Path

import asyncpg
import hvac
import pgvector.asyncpg
from minio import Minio
from minio.error import S3Error

from ingestion.chunker import chunk_pdf
from ingestion.embedder import embed_batch
from ingestion.pdf_extractor import extract_pages
from ingestion.tagger import tag_chunks

# Stable namespace for deterministic chunk UUIDs — never change this value.
_CHUNK_UUID_NS = uuid.UUID("7a6d8f1e-3b2c-4a5e-9f0d-1c2b3a4e5f6d")

# Per-run checkpoint directory — excluded from git via .gitignore.
CACHE_DIR = Path(".ingestion_cache")


# ── Checkpoint helpers ────────────────────────────────────────────────────────


def _chunk_uuid(year: int, session: int, source_type: str, exercise_id: int) -> str:
    """Deterministic UUID for a chunk so re-runs upsert rather than duplicate."""
    return str(uuid.uuid5(_CHUNK_UUID_NS, f"lmc:{year}:{session}:{source_type}:{exercise_id}"))


def _save_stage(filename: str, data: list[dict]) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    (CACHE_DIR / filename).write_text(json.dumps(data))
    print(f"[ingestion] Checkpoint saved → {filename}")


def _load_stage(filename: str) -> list[dict] | None:
    p = CACHE_DIR / filename
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    print(f"[ingestion] Loaded checkpoint {filename} ({len(data)} chunks)")
    return data


def _clear_cache() -> None:
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print("[ingestion] Checkpoint cache cleared")


# ── Vault / MinIO helpers ─────────────────────────────────────────────────────


def _read_vault_secrets(vault_addr: str, vault_token: str) -> dict:
    """Read application secrets from Vault KV v2 at secret/lebanese-math-coach."""
    client = hvac.Client(url=vault_addr, token=vault_token)
    if not client.is_authenticated():
        raise SystemExit(
            f"Vault at {vault_addr} is unreachable or token is invalid.\n"
            "Ensure Vault is running and VAULT_TOKEN is correct."
        )
    try:
        response = client.secrets.kv.v2.read_secret_version(
            path="lebanese-math-coach",
            mount_point="secret",
        )
        return response["data"]["data"]
    except Exception as exc:
        raise SystemExit(f"Failed to read secrets from Vault: {exc}") from exc


def filename_to_meta(name: str) -> tuple[int, int]:
    """Parse (year, session) from a PDF filename.

    session=0 is the sentinel for Exceptional sessions.
    """
    m = re.search(r"Math_GS_English_(\d{4})_Session(\d+)", name)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"Math_GS_English_(\d{4})_Exceptional", name, re.IGNORECASE)
    if m:
        return int(m.group(1)), 0
    raise ValueError(f"Unrecognised filename pattern: {name}")


def upload_pdfs(pdf_dir: str, minio_client: Minio) -> list[str]:
    """Upload all PDFs from pdf_dir to the past-exams MinIO bucket.

    Skips files already present in the bucket. Returns list of uploaded filenames.
    """
    bucket = "past-exams"
    uploaded: list[str] = []
    for pdf_path in sorted(Path(pdf_dir).glob("*.pdf")):
        name = pdf_path.name
        try:
            minio_client.stat_object(bucket, name)
            print(f"[ingestion] Skipping {name} (already in MinIO)")
            continue
        except S3Error:
            pass
        data = pdf_path.read_bytes()
        minio_client.put_object(bucket, name, BytesIO(data), len(data))
        print(f"[ingestion] Uploaded {name}")
        uploaded.append(name)
    return uploaded


# ── Pipeline ──────────────────────────────────────────────────────────────────


def _has_unknowns(chunks: list[dict]) -> bool:
    return any(not c.get("topic") or c["topic"] == "Unknown" for c in chunks)


async def run_pipeline(
    pdf_dir: str,
    db_url: str,
    anthropic_key: str,
    voyage_key: str,
    minio_url: str,
    minio_access: str,
    minio_secret: str,
    force: bool = False,
) -> None:
    if force:
        _clear_cache()

    # asyncpg expects postgresql:// not postgresql+asyncpg://
    db_url_asyncpg = db_url.replace("postgresql+asyncpg://", "postgresql://")

    minio_host = minio_url.replace("http://", "").replace("https://", "")
    secure = minio_url.startswith("https://")
    minio_client = Minio(
        minio_host, access_key=minio_access, secret_key=minio_secret, secure=secure
    )

    bucket = "past-exams"
    if not minio_client.bucket_exists(bucket):
        minio_client.make_bucket(bucket)
        print(f"[ingestion] Created MinIO bucket '{bucket}'")

    upload_pdfs(pdf_dir, minio_client)

    # ── Stage 1: Extract + chunk ──────────────────────────────────────────────
    # Skipped if 01_chunks.json exists and we have a later-stage checkpoint too.
    # The embedded checkpoint takes priority; fall through the stages as needed.

    embedded = _load_stage("03_embedded.json")

    if embedded is not None:
        all_chunks = embedded
        # A stale embedded cache may still carry Unknown topics — handled below.
    else:
        tagged = _load_stage("02_tagged.json")
        if tagged is not None:
            all_chunks = tagged
        else:
            raw = _load_stage("01_chunks.json")
            if raw is None:
                # Run extraction from MinIO
                raw = []
                for obj in minio_client.list_objects(bucket):
                    name = obj.object_name
                    print(f"[ingestion] Processing {name}...")
                    try:
                        year, session = filename_to_meta(name)
                    except ValueError as exc:
                        print(f"[ingestion] WARNING: {exc} — skipping")
                        continue

                    response = minio_client.get_object(bucket, name)
                    try:
                        pdf_bytes = response.read()
                    finally:
                        response.close()
                        response.release_conn()

                    pages = extract_pages(pdf_bytes)
                    chunks = chunk_pdf(pages, year, session)
                    print(f"[ingestion] Extracted {len(chunks)} chunks from {name}")
                    raw.extend(chunks)

                if not raw:
                    print("[ingestion] No chunks extracted — check PDF content and exercise headings")
                    return

                _save_stage("01_chunks.json", raw)

            all_chunks = raw

        # ── Stage 2: Tag ──────────────────────────────────────────────────────
        if _has_unknowns(all_chunks):
            CACHE_DIR.mkdir(exist_ok=True)
            progress_file = CACHE_DIR / "02_tagging_progress.json"
            print(f"[ingestion] Tagging {len(all_chunks)} chunks via claude-haiku...")
            all_chunks = tag_chunks(all_chunks, anthropic_key, progress_file=progress_file)
            _save_stage("02_tagged.json", all_chunks)
            if progress_file.exists():
                progress_file.unlink()
        else:
            print(f"[ingestion] All {len(all_chunks)} chunks tagged — skipping stage 2")

        # ── Stage 3: Embed ────────────────────────────────────────────────────
        print(f"[ingestion] Embedding {len(all_chunks)} chunks via voyage-large-2...")
        all_chunks = embed_batch(all_chunks, voyage_key)
        _save_stage("03_embedded.json", all_chunks)

    # Re-tag Unknown topics in an existing embedded checkpoint without re-embedding.
    # Embeddings are content-based; only the metadata needs updating.
    if _has_unknowns(all_chunks):
        CACHE_DIR.mkdir(exist_ok=True)
        progress_file = CACHE_DIR / "02_tagging_progress.json"
        unknowns = sum(1 for c in all_chunks if not c.get("topic") or c["topic"] == "Unknown")
        print(f"[ingestion] Re-tagging {unknowns} Unknown chunks (embeddings unchanged)...")
        all_chunks = tag_chunks(all_chunks, anthropic_key, progress_file=progress_file)
        _save_stage("03_embedded.json", all_chunks)
        if progress_file.exists():
            progress_file.unlink()

    # ── Stage 4: Insert into PostgreSQL ───────────────────────────────────────
    print("[ingestion] Inserting into pgvector...")
    conn = await asyncpg.connect(db_url_asyncpg)
    # Register vector codec so asyncpg can serialise list[float] → vector column
    await pgvector.asyncpg.register_vector(conn)

    try:
        rows = [
            (
                _chunk_uuid(c["year"], c["session"], c["source_type"], c["exercise_id"]),
                c["source_type"],
                c["year"],
                c["session"],
                c["exercise_id"],
                c["topic"],
                c["subtopic"],
                c["question_type"],
                c["marks"],
                c["content"],
                c["embedding"],
            )
            for c in all_chunks
        ]
        await conn.executemany(
            """
            INSERT INTO chunks
              (id, source_type, year, session, exercise_id, topic, subtopic,
               question_type, marks, content, embedding)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            ON CONFLICT (id) DO UPDATE SET
                topic         = EXCLUDED.topic,
                subtopic      = EXCLUDED.subtopic,
                question_type = EXCLUDED.question_type,
                embedding     = EXCLUDED.embedding
            """,
            rows,
        )
        print(f"[ingestion] Upserted {len(rows)} chunk rows")

        # Derive topic_stats from ingested question chunks
        await conn.execute(
            """
            INSERT INTO topic_stats
              (id, topic, subtopic, appearances, last_seen_year, last_seen_session)
            SELECT
                gen_random_uuid(),
                topic,
                MAX(subtopic),
                COUNT(*),
                MAX(year),
                MAX(session)
            FROM chunks
            WHERE source_type = 'past_exam'
            GROUP BY topic
            ON CONFLICT (topic) DO UPDATE
              SET appearances       = EXCLUDED.appearances,
                  last_seen_year    = EXCLUDED.last_seen_year,
                  last_seen_session = EXCLUDED.last_seen_session
            """
        )
        topic_count = await conn.fetchval("SELECT COUNT(*) FROM topic_stats")
        print(f"[ingestion] Updated topic_stats ({topic_count} topics)")
        print(f"[ingestion] Complete: {len(rows)} chunks, {topic_count} topics")

        # Clear checkpoints only after a fully successful DB write
        _clear_cache()

    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Lebanese Math Coach ingestion pipeline")
    parser.add_argument("--pdf-dir", default="Math_GS_Exams_English")
    parser.add_argument(
        "--db-url",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:devpassword@localhost:5432/lebanese_math",
        ),
    )
    parser.add_argument(
        "--vault-addr",
        default=os.getenv("VAULT_ADDR", "http://localhost:8200"),
    )
    parser.add_argument("--vault-token", default=os.getenv("VAULT_TOKEN", ""))
    parser.add_argument("--minio-url", default="http://localhost:9000")
    parser.add_argument("--minio-access", default="minioadmin")
    parser.add_argument("--minio-secret", default="minioadmin")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Clear checkpoint cache and restart all stages from scratch",
    )
    args = parser.parse_args()

    print(f"[ingestion] Reading secrets from Vault at {args.vault_addr}...")
    secrets = _read_vault_secrets(args.vault_addr, args.vault_token)

    asyncio.run(
        run_pipeline(
            pdf_dir=args.pdf_dir,
            db_url=args.db_url,
            anthropic_key=secrets["anthropic_api_key"],
            voyage_key=secrets["voyage_api_key"],
            minio_url=args.minio_url,
            minio_access=args.minio_access,
            minio_secret=args.minio_secret,
            force=args.force,
        )
    )
