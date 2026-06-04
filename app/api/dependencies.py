"""FastAPI Depends() functions.

These provide db sessions, redis, and secrets to routers
without routers touching infrastructure directly.
"""
from typing import AsyncGenerator

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infra.vault import AppSecrets

# Engine and sessionmaker are initialised lazily on first request
# using the db_url from app.state.secrets.
_sessionmaker: async_sessionmaker | None = None


def _get_sessionmaker(db_url: str) -> async_sessionmaker:
    global _sessionmaker
    if _sessionmaker is None:
        engine = create_async_engine(db_url, echo=False)
        _sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    return _sessionmaker


async def get_async_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    secrets: AppSecrets = request.app.state.secrets
    maker = _get_sessionmaker(secrets.db_url)
    async with maker() as session:
        yield session


async def get_redis(request: Request) -> Redis:
    return request.app.state.redis


async def get_secrets(request: Request) -> AppSecrets:
    return request.app.state.secrets
