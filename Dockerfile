# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

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

# pip cache mount: downloaded wheels are reused on subsequent rebuilds even when
# source changes invalidate this layer. Hatchling needs app/ present to build the wheel.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
