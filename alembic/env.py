import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

# Import all ORM models so Alembic autogenerate detects them.
# This import must stay even though the names are unused here.
from app.repositories.orm import Base  # noqa: F401
import app.repositories.orm  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# DATABASE_URL is injected by the migrate service in docker-compose.yml.
# The migrate container does NOT call resolve_secrets() — it receives DATABASE_URL directly.
database_url = os.environ["DATABASE_URL"]
config.set_main_option("sqlalchemy.url", database_url)


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


run_migrations_online()
