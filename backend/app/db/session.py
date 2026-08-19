"""Async engine and session setup for PostgreSQL.

FastAPI routes get a session through get_session, which is an async
generator so the session is always closed even if the route raises.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """One engine per process. The engine owns the connection pool, so
    creating several would mean several pools competing for connections."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency. Yields a session and closes it afterwards."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def create_all() -> None:
    """Create the extension and every table.

    Development only. Once the schema settles this gets replaced by Alembic,
    because create_all cannot alter an existing table.
    """
    from sqlalchemy import text

    from app.models.schema import Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Close the pool cleanly on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None