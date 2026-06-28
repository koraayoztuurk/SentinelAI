"""PostgreSQL async engine and session factory.

Creates the SQLAlchemy async engine and session factory for the persistence
foundation. The engine is created lazily and opens no network connections until
first use, so application startup and unit tests do not require a live database.
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

    return create_async_engine(settings.dsn, pool_pre_ping=True)


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine."""

    return async_sessionmaker(engine, expire_on_commit=False)
