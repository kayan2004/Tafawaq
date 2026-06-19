# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# apt cache mount: packages are cached across rebuilds, no manual cleanup needed.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl

COPY pyproject.toml .
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini alembic.ini
COPY ingestion/ ingestion/
COPY prompts/ prompts/
COPY Math_GS_Exams_English/ Math_GS_Exams_English/

# uv cache mount: wheels are reused across rebuilds. Hatchling needs app/ present to build the wheel.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system .

# Presidio's default AnalyzerEngine() auto-downloads en_core_web_lg via a `pip`
# subprocess that doesn't exist in this uv-managed image and crashes with
# SystemExit (verified during design) — install the small model explicitly
# via direct wheel URL instead of `spacy download`.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
