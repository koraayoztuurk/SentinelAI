---
title: ADR-003 Polyglot Persistence
status: Accepted
date: 2026-06-27
decision-makers: SentinelAI Team
---

# ADR-003: Polyglot Persistence

## Status

**Accepted**

---

## Context

SentinelAI manages several fundamentally different categories of data.

Examples include:

- transactional investigation data
- graph relationships
- semantic embeddings

These data types have different storage, retrieval and query requirements.

No single database technology provides an optimal solution for every workload.

The platform therefore requires a persistence strategy that balances correctness, performance and maintainability.

---

## Decision

SentinelAI adopts a polyglot persistence architecture.

Different storage technologies are responsible for different categories of information.

The selected storage responsibilities are:

**PostgreSQL**

- investigation data
- evidence metadata
- findings
- reports
- users
- application state

**Neo4j**

- entities
- relationships
- attack paths
- graph traversals

**Vector Database**

- embeddings
- semantic retrieval
- similarity search

Each storage technology owns its respective data domain.

Business services access persistence only through dedicated backend services.

Direct database access from AI components or the frontend is prohibited.

---

## Rationale

Each storage technology is optimized for a specific workload.

Separating persistence responsibilities provides:

- improved query performance
- clearer ownership
- independent scalability
- technology flexibility
- simplified maintenance

The architecture avoids forcing one database technology to solve unrelated problems.

---

## Alternatives Considered

### PostgreSQL Only

A relational-only architecture was considered.

Although operationally simple, graph traversal and semantic retrieval would become increasingly inefficient.

**Decision:** Rejected.

---

### Neo4j Only

A graph-only architecture was considered.

Transactional consistency, relational queries and structured application data would become unnecessarily complex.

**Decision:** Rejected.

---

### Vector Database Only

Using a vector database as the primary persistence layer was considered.

Vector similarity search does not replace transactional storage or graph relationships.

**Decision:** Rejected.

---

### Document Database

A document-oriented database was considered.

While flexible for unstructured documents, it provides no meaningful advantage for graph reasoning or transactional consistency.

**Decision:** Rejected.

---

## Consequences

### Positive

- Storage technologies remain specialized.
- Better query performance.
- Clear ownership of persistence.
- Independent scalability.
- Technology independence.

---

### Negative

- Multiple databases increase operational complexity.
- Cross-database synchronization becomes necessary.
- Additional monitoring is required.

---

### Trade-Offs

The selected architecture accepts higher infrastructure complexity in exchange for better scalability, maintainability and long-term flexibility.

---

## Related Documents

- Database Architecture
- Knowledge Graph
- RAG Architecture
- Graph Service
- Memory Service

---

## Notes

Database responsibilities are considered architectural boundaries.

Future persistence technologies may replace existing implementations provided they preserve the ownership model established by this decision.

Each backend service owns only its designated schemas and tables, even when multiple services share the same PostgreSQL instance.

---

## Supersedes

None