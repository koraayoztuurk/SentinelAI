"""Shared helpers for the live PostgreSQL tests (ES-040).

Plain helper functions (no pytest fixtures, per the test conventions). The
live suite is opt-in (`pytest -m live`) and expects a reachable PostgreSQL
described by the standard ``POSTGRES_*`` environment variables — locally the
compose ``data`` profile publishes it on ``127.0.0.1:5432``
(``POSTGRES_HOST=localhost``); in CI a service container provides it.

``ensure_schema`` migrates the database to the Alembic head once per test
process; every test starts by truncating the tables it touches, so tests stay
order-independent.
"""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import command
from app.config.database import PostgresSettings
from app.infrastructure.persistence.postgres.engine import create_engine

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_schema_ready = False


def alembic_config() -> Config:
    """Return the project Alembic configuration."""

    config = Config(str(_BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    return config


def ensure_schema() -> None:
    """Upgrade the live database to the Alembic head (once per process)."""

    global _schema_ready
    if _schema_ready:
        return
    command.upgrade(alembic_config(), "head")
    _schema_ready = True


def live_engine() -> AsyncEngine:
    """Create an async engine for the live database from the environment."""

    return create_engine(PostgresSettings())


async def truncate_tables(engine: AsyncEngine, *tables: str) -> None:
    """Empty the given tables (and dependents, via CASCADE) between tests."""

    async with engine.begin() as connection:
        await connection.execute(
            text(f"TRUNCATE TABLE {', '.join(tables)} CASCADE")
        )
