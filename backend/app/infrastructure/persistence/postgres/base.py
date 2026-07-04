"""Declarative base for the PostgreSQL ORM models.

Single SQLAlchemy declarative base shared by every service-owned PostgreSQL
schema (each backend service owns its own tables inside the shared instance;
the shared base only provides the metadata and a deterministic constraint
naming convention so migrations stay reproducible).
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Deterministic constraint/index names: hand-written migrations and future
# autogenerate runs produce identical schemas.
_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base carrying the shared metadata and naming convention."""

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)
