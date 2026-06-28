"""PostgreSQL session management.

Provides an async unit-of-work context manager that yields a session and commits
on success or rolls back on error. It contains no business logic; transactional
behaviour and entity mapping are the responsibility of the services that own the
corresponding data.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a transactional async session, committing on success.

    The session is rolled back if the enclosed block raises, and is always
    closed when the context exits.
    """

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
