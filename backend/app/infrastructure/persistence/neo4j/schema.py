"""Neo4j graph schema migration mechanism (ES-048).

The graph model evolves as governed as the relational model (graph-service
§11a): structural definitions — constraints and indexes — are applied through
**versioned, ordered, idempotent** migration steps owned by the Graph Service,
and the current schema version is recorded **in the graph itself** so any
environment's state is identifiable and reproducible.

Design decisions (recorded in the tracker):

- The version marker is a single ``(:SchemaVersion {id:'graph'})`` node with a
  **generic** integer ``version`` — it tracks *any* migration, not only
  structural ones. Future migrations (e.g. a relationship-type vocabulary,
  deferred this slice) are additional steps that bump the same marker, so the
  mechanism does not need reopening when that discipline arrives.
- Relationship semantic types are stored as a **property** on a single Neo4j
  relationship type (``REL``), never embedded in constraints. This is exactly
  what makes the vocabulary deferrable: adding it later is a Graph-Service-level
  write-validation step, not a schema-structure change.

Each step's statements are individually idempotent (``IF NOT EXISTS``); the
version gate additionally prevents re-running already-applied steps. Schema
commands auto-commit, so they run outside a managed transaction.
"""

from neo4j import AsyncDriver

# Ordered migration steps: (version, statements). Append new steps with the
# next integer version; never edit or reorder shipped steps.
_MIGRATIONS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (
        1,
        (
            # Entity identity is the canonical key (Domain Rule 3): globally
            # unique. The uniqueness constraint also provides the lookup index.
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
            "FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            # Relationships carry a caller-supplied id; a property index makes
            # get-by-id lookups efficient. Not a uniqueness constraint
            # (relationship uniqueness needs a specific edition/version; the
            # application supplies unique ids), so it stays Community-compatible.
            "CREATE INDEX rel_id_index IF NOT EXISTS "
            "FOR ()-[r:REL]-() ON (r.id)",
        ),
    ),
)

_ENSURE_VERSION_NODE = (
    "MERGE (v:SchemaVersion {id: 'graph'}) "
    "ON CREATE SET v.version = 0 "
    "RETURN v.version AS version"
)
_READ_VERSION = (
    "MATCH (v:SchemaVersion {id: 'graph'}) RETURN v.version AS version"
)
_SET_VERSION = "MATCH (v:SchemaVersion {id: 'graph'}) SET v.version = $version"


def head_version() -> int:
    """Return the latest declared schema version (the migration head)."""

    return _MIGRATIONS[-1][0] if _MIGRATIONS else 0


async def current_version(driver: AsyncDriver) -> int:
    """Return the schema version currently recorded in the graph (0 if none)."""

    async with driver.session() as session:
        record = await (await session.run(_READ_VERSION)).single()
    return int(record["version"]) if record is not None else 0


async def bootstrap_graph_schema(driver: AsyncDriver) -> int:
    """Apply pending migrations to the graph and return the resulting version.

    Idempotent: re-running against an up-to-date graph is a no-op. Deterministic:
    an empty graph is migrated to :func:`head_version`. Callable from the live
    test setup and the demo seed utility; not run in the default app lifespan
    (startup must not require a live graph store).
    """

    async with driver.session() as session:
        record = await (await session.run(_ENSURE_VERSION_NODE)).single()
        current = int(record["version"]) if record is not None else 0

        for version, statements in _MIGRATIONS:
            if version <= current:
                continue
            # Schema commands auto-commit; run them one by one on the
            # auto-commit session (not inside a managed transaction).
            for statement in statements:
                await (await session.run(statement)).consume()
            await (await session.run(_SET_VERSION, version=version)).consume()
            current = version

    return current
