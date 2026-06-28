"""Persistence infrastructure.

Provides connection and session management for the polyglot persistence stores
(PostgreSQL, Neo4j, Qdrant and Redis) defined by the Database Architecture.

This package is the persistence foundation (ES-004). It owns only the lifecycle
of long-lived connection resources and the session seams that future services
build upon. It contains no concrete repositories, ORM table models, graph schema
or vector collections — those are owned by the backend services (ES-005/006).
"""
