"""Neo4j GraphRepository adapter (ES-048).

Concrete implementation of the Graph Service's repository port
(:class:`~app.application.graph.repositories.GraphRepository`) over the Neo4j
async driver — the real authoritative store for Entity/Relationship (ADR-003;
database-architecture §9). Replaces the ES-042 ``UnavailableGraphRepository``
in the runtime binding.

Relationship modelling: every relationship is a single Neo4j type ``REL`` whose
domain type is a property (mappers.py), so the open-string relationship-type
vocabulary is never embedded in the graph structure. Traversal (`neighbors`)
walks ``REL`` edges regardless of their semantic type.

Each method runs in its own managed read/write transaction (automatic transient
retry). Neo4j is a separate bounded context: there is no cross-store
transaction with PostgreSQL (identifiers are the only cross-store reference,
§8a). Driver-level unavailability (the store is unreachable) is mapped to the
stable :class:`~app.application.graph.errors.GraphStoreUnavailableError`
(``graph.store_unavailable``) — the same contract the unavailable stub used —
so the Planner Service still contains it as a failed execution result and the
Graph API translates it to 503.
"""

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from neo4j import AsyncDriver, AsyncManagedTransaction
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from app.application.graph.errors import GraphStoreUnavailableError
from app.domain.entity import Entity
from app.domain.identifiers import EntityId, RelationshipId
from app.domain.relationship import Relationship
from app.infrastructure.persistence.neo4j.mappers import (
    entity_from_node,
    entity_to_properties,
    relationship_from_record,
    relationship_to_properties,
)

_T = TypeVar("_T")


class Neo4jGraphRepository:
    """``GraphRepository`` adapter over the Neo4j async driver."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    # -------------------------------------------------------------------- entity

    async def add_entity(self, entity: Entity) -> None:
        properties = entity_to_properties(entity)

        async def _work(tx: AsyncManagedTransaction) -> None:
            await tx.run(
                "CREATE (e:Entity) SET e = $properties", properties=properties
            )

        await self._write(_work)

    async def get_entity(self, entity_id: EntityId) -> Entity | None:
        async def _work(tx: AsyncManagedTransaction) -> dict[str, Any] | None:
            result = await tx.run(
                "MATCH (e:Entity {id: $id}) RETURN e AS node", id=entity_id.value
            )
            record = await result.single()
            return dict(record["node"]) if record is not None else None

        node = await self._read(_work)
        return None if node is None else entity_from_node(node)

    async def update_entity(self, entity: Entity) -> None:
        properties = entity_to_properties(entity)

        async def _work(tx: AsyncManagedTransaction) -> None:
            await tx.run(
                "MATCH (e:Entity {id: $id}) SET e = $properties",
                id=entity.id.value,
                properties=properties,
            )

        await self._write(_work)

    async def erase_entity(self, entity: Entity) -> None:
        """Overwrite the node with its tombstone properties (ES-065).

        The node is not deleted: its identifier survives so relationships
        referencing it still resolve to an explicit erased node (§8a). Same
        write shape as ``update_entity``; the caller supplies the tombstone.
        """

        properties = entity_to_properties(entity)

        async def _work(tx: AsyncManagedTransaction) -> None:
            await tx.run(
                "MATCH (e:Entity {id: $id}) SET e = $properties",
                id=entity.id.value,
                properties=properties,
            )

        await self._write(_work)

    # -------------------------------------------------------------- relationship

    async def add_relationship(self, relationship: Relationship) -> None:
        properties = relationship_to_properties(relationship)

        async def _work(tx: AsyncManagedTransaction) -> None:
            await tx.run(
                "MATCH (s:Entity {id: $source}), (t:Entity {id: $target}) "
                "CREATE (s)-[r:REL]->(t) SET r = $properties",
                source=relationship.source_entity_id.value,
                target=relationship.target_entity_id.value,
                properties=properties,
            )

        await self._write(_work)

    async def get_relationship(
        self, relationship_id: RelationshipId
    ) -> Relationship | None:
        async def _work(tx: AsyncManagedTransaction) -> dict[str, Any] | None:
            result = await tx.run(
                "MATCH (s:Entity)-[r:REL {id: $id}]->(t:Entity) "
                "RETURN r AS rel, s.id AS source, t.id AS target",
                id=relationship_id.value,
            )
            record = await result.single()
            if record is None:
                return None
            return {
                "rel": dict(record["rel"]),
                "source": record["source"],
                "target": record["target"],
            }

        found = await self._read(_work)
        if found is None:
            return None
        return relationship_from_record(
            found["rel"], found["source"], found["target"]
        )

    async def update_relationship(self, relationship: Relationship) -> None:
        properties = relationship_to_properties(relationship)

        async def _work(tx: AsyncManagedTransaction) -> None:
            # Endpoints never change; only the relationship's own properties.
            await tx.run(
                "MATCH ()-[r:REL {id: $id}]->() SET r = $properties",
                id=relationship.id.value,
                properties=properties,
            )

        await self._write(_work)

    async def list_relationships_for_entity(
        self, entity_id: EntityId
    ) -> tuple[Relationship, ...]:
        async def _work(tx: AsyncManagedTransaction) -> list[dict[str, Any]]:
            result = await tx.run(
                "MATCH (e:Entity {id: $id})-[r:REL]-(o:Entity) "
                "RETURN r AS rel, startNode(r).id AS source, "
                "endNode(r).id AS target, r.id AS rid ORDER BY rid",
                id=entity_id.value,
            )
            return [
                {
                    "rel": dict(record["rel"]),
                    "source": record["source"],
                    "target": record["target"],
                }
                async for record in result
            ]

        rows = await self._read(_work)
        return tuple(
            relationship_from_record(row["rel"], row["source"], row["target"])
            for row in rows
        )

    # ----------------------------------------------------------------- traversal

    async def neighbors(
        self, entity_id: EntityId, depth: int, max_nodes: int
    ) -> tuple[Entity, ...]:
        # `depth` bounds the variable-length pattern. Neo4j does not allow a
        # parameterized upper bound in `*1..N`, so the validated integer is
        # interpolated (never a caller string); `max_nodes` is parameterized.
        hops = max(1, int(depth))
        query = (
            f"MATCH (e:Entity {{id: $id}})-[:REL*1..{hops}]-(n:Entity) "
            "WHERE n.id <> $id "
            "RETURN DISTINCT n AS node ORDER BY n.id LIMIT $max_nodes"
        )

        async def _work(tx: AsyncManagedTransaction) -> list[dict[str, Any]]:
            result = await tx.run(query, id=entity_id.value, max_nodes=max_nodes)
            return [dict(record["node"]) async for record in result]

        nodes = await self._read(_work)
        return tuple(entity_from_node(node) for node in nodes)

    # ------------------------------------------------------------------- helpers

    async def _read(
        self, work: Callable[[AsyncManagedTransaction], Awaitable[_T]]
    ) -> _T:
        try:
            async with self._driver.session() as session:
                return await session.execute_read(work)
        except (ServiceUnavailable, SessionExpired, OSError) as exc:
            raise GraphStoreUnavailableError(
                "The graph store is unreachable."
            ) from exc

    async def _write(
        self, work: Callable[[AsyncManagedTransaction], Awaitable[None]]
    ) -> None:
        try:
            async with self._driver.session() as session:
                await session.execute_write(work)
        except (ServiceUnavailable, SessionExpired, OSError) as exc:
            raise GraphStoreUnavailableError(
                "The graph store is unreachable."
            ) from exc
