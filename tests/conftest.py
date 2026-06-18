"""Shared pytest fixtures — integration tests run against the real dev Postgres
(SQLite is unsupported by this codebase; see CLAUDE.md). Requires `docker compose
up db` to be running.
"""
from __future__ import annotations

import os

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:devpassword@localhost:5432/lebanese_math",
)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(_DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()
