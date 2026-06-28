"""Infrastructure layer.

Provides the technical capabilities required by higher layers: persistence
adapters and external integrations. Per the Database Architecture and ADR-004,
each storage technology is accessed only through its owning service
(PostgreSQL, Neo4j and the Vector Database).

Infrastructure implements interfaces defined by inner layers and remains
replaceable. This layer is intentionally empty in the backend skeleton (ES-002)
and is populated by ES-004 through ES-006.
"""
