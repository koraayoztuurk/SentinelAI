---
title: ADR-011 Supporting Persistence Technologies
status: Accepted
date: 2026-07-03
decision-makers: SentinelAI Team
---

# ADR-011: Supporting Persistence Technologies

## Status

**Accepted**

---

## Context

ADR-003 established the polyglot persistence architecture and assigned domain-data ownership to three primary storage technologies: PostgreSQL, Neo4j and a vector database.

The platform additionally provisions **Redis** — in the deployment stack, the configuration model and the persistence lifecycle registry — as a caching technology. The Database Architecture document describes its constraints in detail, but no architectural decision record ever admitted a fourth persistence technology.

This left a governance gap: a storage technology entered the architecture outside the ADR process, and ADR-003 contained no category for persistence technologies that do **not** own domain data.

An explicit decision was required so that the caching layer's existence, constraints and limits are governed rather than implied.

---

## Decision

### 1. A supporting-persistence category is introduced

The persistence architecture distinguishes two categories:

- **Primary storage technologies** own domain data (ADR-003, unchanged).
- **Supporting persistence technologies** improve performance and hold transient operational state. They are **never authoritative**: they own no domain object, all of their content must be reproducible from primary storage, and removing all of their data must not affect business correctness.

### 2. Redis is the platform's supporting persistence technology for caching

Redis is adopted for:

- caching derived or frequently read representations
- short-lived operational state

Redis is subject to the following constraints (normative, per the Database Architecture):

- Redis never becomes the primary source of business information.
- Cache population and invalidation never replace writes to authoritative storage.
- Redis does not participate in transactional consistency; temporary cache inconsistencies are acceptable while authoritative storage remains correct.
- Redis availability must not determine system availability: on cache failure, services fall back to authoritative storage and accept degraded performance.

### 3. Integration is demand-driven

Cache integration is introduced only when an owning backend service has a documented performance need. Provisioned-but-unconsumed caching (the current state) is acceptable for the deployment foundation but confers no license to route business data through the cache.

---

## Rationale

- The category ("supporting, never authoritative") is the architecturally significant decision; the product choice (Redis) is replaceable under it.
- Making the constraints an ADR-level commitment prevents the most common cache failure mode: the cache silently becoming a second source of truth.
- Demand-driven integration keeps the platform honest about complexity: infrastructure that exists must not attract responsibilities it was never granted.

---

## Alternatives Considered

### Extending ADR-003 in place

Rewriting the accepted polyglot-persistence decision to add Redis was considered.

Accepted decisions are historical records; silently editing them erases the reasoning trail this ADR process exists to preserve.

**Decision:** Rejected.

---

### Treating Redis as a fourth primary storage technology

Assigning Redis ownership of some category of domain data was considered.

Cached data is by definition reproducible; granting it ownership would create a second source of truth and violate the single-ownership model of ADR-003.

**Decision:** Rejected.

---

### Removing Redis until a consumer exists

Dropping the provisioned cache from the stack until a service needs it was considered.

The deployment, configuration and lifecycle foundations already treat the data tier as one opt-in unit, and the cost of the provisioned-but-idle cache is near zero (opt-in compose profile, lazy startup). Removing and reintroducing it would churn the deployment foundation without reducing any risk that the "never authoritative" constraints do not already control.

**Decision:** Rejected.

---

## Consequences

### Positive

- The fourth persistence technology is governed, with explicit constraints and an explicit non-ownership guarantee.
- The supporting-persistence category gives future technologies (for example, an object store for uploads) a defined entry path.
- Cache-failure behavior is an ADR-level commitment, not an implementation preference.

### Negative

- One more ADR to maintain.
- The demand-driven rule means cache integration requires justification work when it eventually arrives.

### Trade-Offs

The architecture accepts a small amount of governance overhead in exchange for closing the gap through which storage technologies could enter the platform undecided.

---

## Related Documents

- Database Architecture
- ADR-003 Polyglot Persistence
- Configuration Management
- Deployment Architecture

---

## Notes

This ADR **amends ADR-003** by adding the supporting-persistence category. ADR-003's ownership model for primary storage technologies is unchanged.

Redis integration work (cache adapters, invalidation policies) remains deferred implementation (see the implementation tracker, ES-004 technical debt).

---

## Supersedes

None
