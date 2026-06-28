"""Application layer.

Hosts the backend application services that own SentinelAI's business
capabilities as defined by ADR-004 (Backend Service Boundaries): the
Investigation Service, Memory Service, Graph Service and Planner Service.

Application services orchestrate domain objects and depend on infrastructure
through interfaces; they never expose persistence or transport details. This
layer is intentionally empty in the backend skeleton (ES-002) and is populated
by ES-007 through ES-010.
"""
