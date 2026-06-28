"""Neo4j async driver lifecycle.

Creates the Neo4j async driver for the persistence foundation. The driver is
created lazily and verifies no connectivity here, so application startup and unit
tests do not require a live database.
"""

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.config.database import Neo4jSettings


def create_driver(settings: Neo4jSettings) -> AsyncDriver:
    """Create the Neo4j async driver for the given settings."""

    return AsyncGraphDatabase.driver(
        settings.uri,
        auth=(settings.user, settings.password.get_secret_value()),
    )
