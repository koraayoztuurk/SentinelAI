"""PostgreSQL async engine and session factory.

Creates the SQLAlchemy async engine and session factory for the persistence
foundation. The engine is created lazily and opens no network connections until
first use, so application startup and unit tests do not require a live database.

Pool policy (ES-067): size, overflow, checkout timeout and recycle age are
configuration rather than library defaults — the request path and the two
background projectors share one pool, and a bounded checkout wait means an
exhausted pool fails fast instead of hanging a request. ``pool_pre_ping``
remains on so a connection dropped underneath the pool is replaced rather than
surfacing as a query error.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.database import PostgresSettings


def create_engine(settings: PostgresSettings) -> AsyncEngine:
    """Create the async SQLAlchemy engine for the given settings."""

    return create_async_engine(
        settings.dsn,
        pool_pre_ping=True,
        pool_size=settings.pool_size,
        max_overflow=settings.pool_max_overflow,
        pool_timeout=settings.pool_timeout_seconds,
        pool_recycle=settings.pool_recycle_seconds,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine."""

    return async_sessionmaker(engine, expire_on_commit=False)
