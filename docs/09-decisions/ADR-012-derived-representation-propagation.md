---
title: ADR-012 Derived Representation Production and Propagation
status: Accepted
date: 2026-07-03
decision-makers: SentinelAI Team
---

# ADR-012: Derived Representation Production and Propagation

## Status

**Accepted**

---

## Context

The polyglot persistence architecture (ADR-003, ADR-011) assigns every domain object a single authoritative store and allows **derived representations** — secondary copies optimized for another workload. The only derived representation defined today is the Memory Item embedding, synchronized from PostgreSQL to the vector database.

Two questions were left undecided, and both become blocking the moment persistence adapters are implemented:

1. **How do derived representations stay consistent with their authoritative source?** The Database Architecture demands eventual consistency and idempotence but names no mechanism. The Memory Service specification depicted memory creation as a single request chain (PostgreSQL → embedding generation → vector database) — a classic **dual-write**: if the second write fails, no defined recovery exists and the stores silently diverge.

2. **Which layer owns embedding production?** The Memory Service owns embedding management (memory-service.md), but the embedding provider port lives in the AI Runtime (`app/ai/providers/embedding.py`) — and the enforced constraint AC-04 (architecture-testing.md §6) forbids the application layer from depending on the AI Runtime. As written, the first embedding implementation would have to violate either the constraint or the specification (audit finding D-01).

---

## Decision

### 1. Derived representations propagate through a transactional outbox

- A change to an authoritative object and the **intent to derive** are recorded in the **same local transaction** in the authoritative store (the outbox).
- **Asynchronous, idempotent projectors** — owned by the same backend service that owns the authoritative object — consume the outbox and produce/update the derived representation.
- Replay is safe: repeated projection of the same outbox record always yields the same derived state.
- Projection failures never touch the authoritative object; they are retried, and unprocessed outbox records remain observable.

### 2. No request path writes to more than one store

No synchronous request path may write to two stores (authoritative + derived) as one logical operation. The authoritative write commits; propagation is always asynchronous through the outbox. This is a normative architectural constraint (recorded as AC-14 in the Architecture Testing constraint catalogue; mechanically enforceable once adapters exist).

### 3. Embedding production is owned by the application layer behind its own port

- The **Memory Service** (application layer) defines and owns a narrow **embedding port** in its own layer.
- The **infrastructure layer** implements that port; the concrete adapter may internally use the AI Runtime's provider-neutral embedding port or call a provider directly — infrastructure may implement ports from multiple layers.
- The AI Runtime's `EmbeddingProvider` port remains the provider-neutral abstraction for AI-side consumers; the Memory Service never imports it (AC-04 preserved).

### 4. Distributed transactions are rejected

Neither two-phase commit nor saga-style compensation is used for derived representations: a derived copy is reproducible by definition, so eventual, idempotent re-projection is strictly simpler and sufficient.

---

## Rationale

- Dual-write is the single most common way a polyglot system silently loses consistency; recording intent transactionally with the source removes the failure window entirely instead of shrinking it.
- Ownership stays intact: the service that owns the object owns its outbox and its projectors (ADR-004), so no cross-service synchronization component is needed.
- The embedding-port decision resolves audit finding D-01 before it becomes a constraint violation: the specification (Memory Service owns embeddings) and the constraint (application ̸→ AI Runtime) are both preserved by placing the port in the application layer and the implementation in infrastructure.
- Verifiability: "no request writes to two stores" is a checkable property (code review today, static/integration checks once adapters exist), and outbox lag is a measurable operational signal.

---

## Alternatives Considered

### Synchronous dual-write with best-effort retry

The request writes the authoritative store, then the derived store, retrying on failure.

The failure window between the writes is unremovable; a crash after the first write diverges the stores with no record that propagation was owed.

**Decision:** Rejected.

---

### Distributed transactions (2PC) or saga compensation

Coordinated multi-store transactions were considered.

Derived data is reproducible; compensations and coordinators add coupling and operational load to protect data that can simply be re-projected.

**Decision:** Rejected.

---

### Change data capture (log tailing) instead of an outbox

CDC infrastructure was considered.

It introduces a heavy operational dependency for a platform with a single derived representation; the outbox achieves the same guarantee inside the store the service already owns. CDC remains a compatible future replacement for the outbox's transport half.

**Decision:** Rejected (for now).

---

### AI Runtime-side embedding production

Embedding generation performed in the AI Runtime, with the Memory Service accepting vectors as data.

This moves a persistence-coupled responsibility into a layer that must not touch persistence (ADR-005) and splits the ownership of the Memory Item's derived representation across layers.

**Decision:** Rejected.

---

## Consequences

### Positive

- The dual-write failure mode is architecturally impossible, not merely mitigated.
- Embedding implementation has a defined, constraint-compatible home before any code exists.
- Ownership and dependency-direction rules (ADR-004, AC-04) survive the first real persistence work unchanged.

### Negative

- Derived representations are stale for the outbox-to-projection interval (bounded, observable).
- The authoritative store carries the outbox table/collection and its housekeeping.

### Trade-Offs

Bounded staleness of reproducible data is accepted in exchange for the impossibility of silent divergence.

---

## Related Documents

- Database Architecture (§7/§8 Synchronization, §8a Cross-Store References)
- Memory Service (embedding lifecycle and creation flow)
- Architecture Testing (constraint catalogue, AC-14)
- ADR-003 Polyglot Persistence, ADR-011 Supporting Persistence Technologies

---

## Notes

This ADR **amends ADR-003** (adds the propagation mechanism its ownership model presupposed) and resolves audit findings **E-01** and **D-01** (`ARCHITECTURE-GAPS-2026-07-03.md`).

Concrete outbox schema, projector scheduling and the embedding adapter are implementation work that follows the persistence adapters (implementation tracker).

---

## Supersedes

None
