"""Aggregated PostgreSQL ORM metadata.

Single import point that loads every service-owned ORM module so the shared
declarative metadata is fully populated (Alembic's ``target_metadata`` and the
live tests consume it). New service schemas register here as their adapters
are introduced.
"""

from sqlalchemy import MetaData

from app.infrastructure.persistence.postgres import base
from app.infrastructure.persistence.postgres.investigation import (
    orm as investigation_orm,
)
from app.infrastructure.persistence.postgres.memory import orm as memory_orm

__all__ = ["metadata", "investigation_orm", "memory_orm"]

metadata: MetaData = base.Base.metadata
