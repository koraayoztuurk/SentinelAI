---
title: ADR-004 Backend Service Boundaries
status: Accepted
date: 2026-06-27
decision-makers: SentinelAI Team
---

# ADR-004: Backend Service Boundaries

## Status

**Accepted**

---

## Context

SentinelAI consists of multiple backend capabilities responsible for investigation execution, memory management and graph operations.

Without clearly defined service boundaries, business responsibilities would gradually become duplicated across components.

This would increase coupling, complicate maintenance and reduce architectural clarity.

A clear ownership model was therefore required before implementation.

---

## Decision

SentinelAI adopts a service-oriented backend architecture with explicit ownership boundaries.

Each backend service owns a single business capability.

The primary backend services are:

**Investigation Service**

Responsible for:

- investigation lifecycle
- evidence management
- findings
- reports
- investigation workspace

---

**Memory Service**

Responsible for:

- organizational memory
- semantic retrieval
- memory indexing
- memory persistence
- embedding lifecycle

---

**Graph Service**

Responsible for:

- entity management
- relationship management
- graph traversal
- graph validation
- graph persistence

---

Backend services own business capabilities rather than technologies.

No backend service may directly assume responsibilities owned by another service.

---

## Ownership Rules

Business ownership follows strict boundaries.

Investigation Service owns investigations.

Memory Service owns organizational memory.

Graph Service owns graph knowledge.

Ownership must remain unique.

Business responsibilities must never be duplicated across services.

---

## Service Communication

Backend services communicate only through well-defined service interfaces.

Internal implementation details remain private.

Services must exchange business information rather than database objects.

---

## Database Access

Every persistence technology is accessed only through its owning backend service.

Examples include:

- PostgreSQL through Investigation Service or Memory Service
- Neo4j through Graph Service
- Vector Database through Memory Service

Other services must never bypass these ownership boundaries.

---

## Rationale

Explicit service boundaries improve:

- maintainability
- scalability
- testability
- ownership clarity
- independent evolution

The architecture intentionally favors clear responsibility boundaries over convenience.

---

## Alternatives Considered

### Shared Backend Layer

A shared service layer where every component accesses common business logic was considered.

Although implementation would initially appear simpler, ownership would gradually become ambiguous.

**Decision:** Rejected.

---

### Database-Oriented Services

Services organized around database technologies rather than business capabilities were considered.

This approach tightly couples business logic to persistence.

Changing storage technologies would require architectural changes.

**Decision:** Rejected.

---

### Monolithic Business Service

A single backend service responsible for every business capability was considered.

As SentinelAI grows, this approach would create excessive coupling and reduce independent evolution.

**Decision:** Rejected.

---

## Consequences

### Positive

- Clear business ownership.
- Reduced coupling.
- Independent service evolution.
- Improved maintainability.
- Easier testing.

---

### Negative

- Increased service coordination.
- Additional interface definitions.
- Greater architectural discipline required.

---

### Trade-Offs

The selected architecture accepts additional service coordination in exchange for long-term modularity and maintainability.

---

## Related Documents

- Backend Architecture
- Investigation Service
- Memory Service
- Graph Service
- Database Architecture
- API Design

---

## Notes

Business ownership always takes precedence over implementation convenience.

New backend services may be introduced only when they own a distinct business capability.

Existing responsibilities should not be redistributed without introducing a superseding architectural decision.

---

## Supersedes

None