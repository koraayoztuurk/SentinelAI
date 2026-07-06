"""Shared helpers for the live Neo4j tests (ES-048).

Plain helper functions (no pytest fixtures, per the test conventions). The
``live_neo4j`` suite is opt-in and expects a reachable Neo4j published by the
compose ``data`` profile on loopback ``127.0.0.1:7687``.

Symmetric to the Postgres live support: the connection comes from the standard
``NEO4J_*`` environment variables (``app.config.database.Neo4jSettings``). Both
the host-run tests **and** the app under test (its registry driver) read the
same variables, so a single set of overrides configures everything:

    NEO4J_URI=bolt://127.0.0.1:7687   (the compose default URI is the
                                       compose-internal hostname)
    NEO4J_PASSWORD=<the compose password>

``prepare_graph`` bootstraps the schema (idempotent) and clears prior graph
data, so tests stay order-independent.
"""

from neo4j import AsyncDriver

from app.config.database import Neo4jSettings
from app.infrastructure.persistence.neo4j.driver import create_driver
from app.infrastructure.persistence.neo4j.schema import bootstrap_graph_schema


def live_driver() -> AsyncDriver:
    """Create a Neo4j async driver for the live graph store from the environment."""

    return create_driver(Neo4jSettings())


async def clear_graph(driver: AsyncDriver) -> None:
    """Remove all Entity nodes and their relationships (keeps the version node)."""

    async with driver.session() as session:
        await (await session.run("MATCH (n:Entity) DETACH DELETE n")).consume()


async def prepare_graph(driver: AsyncDriver) -> None:
    """Bootstrap the schema and clear prior data before a test."""

    await bootstrap_graph_schema(driver)
    await clear_graph(driver)
