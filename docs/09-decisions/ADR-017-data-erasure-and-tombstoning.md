---
title: ADR-017 Data Erasure and Tombstoning
status: Accepted
date: 2026-07-23
decision-makers: SentinelAI Team
---

# ADR-017: Data Erasure and Tombstoning

## Status

**Accepted** (proposed and reviewed through RFC-003, under ADR-014).

---

## Context

data-lifecycle.md (audit finding M-05) fixes the erasure model — lifecycle
ownership per category, deprecation ≠ deletion, erasure follows ownership and
references, derived data is erased with its source, and the tombstoning /
crypto-shredding strategy categories — but the document is Draft and no store
has an erasure path. Milestone F (data end-of-life) requires that the erasure
lifecycle exist so retention limits and right-to-be-forgotten requests can be
satisfied by design, not retrofitted into an immutability-first model later.
RFC-003 proposed admitting the erasure lifecycle and a uniform tombstone
protocol; this ADR records the accepted decision.

---

## Decision

### 1. A terminal `Erased` state, orthogonal to the business lifecycle

Domain objects with a documented lifecycle (domain-model.md §15) gain a terminal
`Erased` state. Erasure is not a business transition: an object may be erased
from **any** state, and `Erased` is terminal — no business write or lifecycle
transition follows it. Erasure is an end-of-life operation, distinct from the
business workflow that owns the ordinary transitions.

### 2. Tombstoning preserves only non-personal correlation structure

An erased record is replaced by an explicit erasure marker that keeps:

- **identifiers** (the object's id and the ids it is referenced by),
- **timestamps** (creation, and the erasure timestamp itself), and
- **scope keys** the authorization policy needs — `owner` and `tenant` — so
  post-erasure access decisions still resolve (a tombstone stays owner+tenant
  scoped; its creator can still see that it was erased).

Everything else — titles, descriptions, normalized content, free text, any
personal data — is **redacted** to a tombstone marker. The evidence content
address (a SHA-256 hash) is retained as non-personal correlation structure so
the payload bytes it names can be located and physically erased (ES-065).

### 3. Tombstones resolve explicitly, never silently

A read of an erased object resolves to an explicit "erased" state — it is never
silently dropped, hidden, repaired or fabricated (database-architecture §8a).
An erased investigation and its scoped objects remain addressable; their reads
return the tombstone, not a 404-as-if-never-existed. Erasure is **idempotent**:
re-erasing an already-erased object is a no-op that returns the same tombstone.

### 4. Ownership-scoped cascade; shared knowledge is not cascaded

Erasing an investigation erases its investigation-scoped objects — evidence,
findings, report, outcome and trace, all PostgreSQL-owned through the
Investigation Service — tombstoned in **one local transaction** (one operation
writes one store; AC-14 clean). The append-only trace gains an erasure operation
used only by this end-of-life path; append-only continues to govern business
writes (domain-model.md line 633 already scopes trace removal to the Data
Lifecycle architecture).

Memory and the Knowledge Graph are §6a shared-knowledge layers and are **not**
cascaded by investigation erasure. They carry their own **person-linked**
erasure path (right-to-be-forgotten), owned by the Memory Service and Graph
Service respectively, triggered independently of any single investigation
(ES-065).

### 5. Secondary-store erasure propagates as an idempotent projection

Physical erasure of secondary-store bytes — embeddings in the vector store, raw
payload bytes in the object store — never happens inside the erasure operation.
The erasure **intent is recorded durably in the same local transaction as the
tombstone**, and an asynchronous, idempotent, retriable projector performs the
physical erasure (the ADR-012 model, reused for end-of-life). No erasure
operation writes two stores synchronously (AC-14). Until the projection
completes, the record is tombstoned and the secondary bytes are pending-erasure —
bounded and observable, exactly the ADR-012 staleness model.

The intent takes the form each owning service already has:

- **Embeddings (Memory Service):** the existing ADR-012 `memory_outbox` record,
  written in the same transaction as the tombstoned versions. The projector
  re-reads the item, sees the terminal `ERASED` status and **deletes** the point
  instead of upserting it — one mechanism for both production and erasure.
- **Payload bytes (Investigation Service):** the **tombstone itself is the
  intent** — an evidence tombstone of an erased investigation that still carries
  its content address names bytes that may still exist. The projector erases
  them and then redacts the address, so the projection converges and the record
  stops referencing erased bytes. No separate outbox table is introduced: the
  durability, idempotence and retriability guarantees come from the tombstone
  state itself, written in the erasure transaction.

### 6. Per-store erasure strategy is an adapter choice

The *existence* of an erasure strategy per category is mandatory; *which*
strategy is an adapter-level decision (data-lifecycle §4):

- **Record stores (PostgreSQL, Neo4j):** tombstoning (this decision).
- **Vector store (Qdrant):** point deletion of the derived embedding
  (reproducible; deletion is sufficient).
- **Evidence payload store:** **crypto-shredding** is the designated strategy
  for the immutable production object store (physical deletion from
  content-addressed / append-only storage is impractical, §4). The **dev-grade
  filesystem adapter** erases by **physical deletion** — practical on a mutable
  single-node filesystem — with content-address de-duplication a documented
  dev-grade limitation (two evidences sharing a payload share one file; the
  production per-unit crypto-shred resolves it, Milestone G). The
  `EvidencePayloadStore` port gains an erase operation (ES-065).

### 7. Erasure is audited

Every erasure operation is a security-relevant action recorded through the
existing operation-audit boundary — who requested it, when (§5). No new audit
vocabulary is introduced here; a dedicated erasure-category audit action rides
the richer-audit-vocabulary work (ES-021 TD / Milestone H). Trace entries are
investigation-scoped and follow the investigation's erasure — they are **not**
part of the audit exception (§5).

---

## Rationale

- data-lifecycle.md already fixed the model; this realizes it without inventing
  new semantics — tombstoning, the ownership cascade and the outbox projection
  are the documented principles, now decided.
- Tombstoning (vs hard delete) keeps §8a's observability: "erased" is
  distinguishable from "never existed", and correlation/audit structure
  survives — the property a security platform needs most at end-of-life.
- Routing secondary-store erasure through the outbox keeps the one-store-per-
  operation constraint that protects the platform from silent divergence — the
  same guarantee ADR-012 gave production, reused for end-of-life.
- Retaining owner/tenant on the tombstone means the erasure lifecycle needs no
  new authorization path: an erased investigation is still owner+tenant scoped.

---

## Alternatives Considered

See RFC-003 (hard delete; deprecation-as-erasure; synchronous multi-store
erasure; a single cross-service erasure component) — all dismissed there with
rationale.

---

## Consequences

### Positive

- The platform can satisfy retention and right-to-be-forgotten by design; the
  immutability-first model no longer blocks erasure.
- Erased state is explicit and observable end to end (§8a), and every erasure is
  audited.
- Secondary-store erasure inherits ADR-012's idempotence and retriability — a
  crashed erasure resumes, never diverges.

### Negative

- Secondary bytes (embeddings, payloads) are pending-erasure for the
  outbox-to-projection interval — bounded and observable, not instantaneous.
- The dev filesystem payload adapter's physical delete interacts with content-
  address dedup (shared payloads) — a documented dev-grade limitation until the
  production crypto-shred adapter (Milestone G).
- Automated retention enforcement is not yet present; erasure is request- or
  policy-triggered until the Milestone G sweeper.

### Trade-Offs

Bounded pending-erasure of secondary bytes is accepted in exchange for the
one-store-per-operation guarantee — the same trade ADR-012 made for derived
data, now applied to its end-of-life.

---

## Related Documents

- RFC-003 Data Erasure and Tombstoning
- Data Lifecycle and Erasure (data-lifecycle.md — §2 ownership, §3 principles,
  §4 strategies, §5 audit exception)
- Database Architecture (§8a Cross-Store References, §8b Evidence Payload
  Storage)
- Domain Model (§15 Domain Object Lifecycle; trace removal note, line 633)
- ADR-003 Polyglot Persistence (amended: ownership gains an end-of-life
  dimension)
- ADR-012 Derived Representation Propagation (extended: erasure as a projection)
- ADR-015 Evidence Payload Store (extended: the port gains an erase operation)

---

## Notes

This ADR **amends ADR-003** by adding an end-of-life (erasure) dimension to the
ownership model — each owner also owns its category's erasure path; ADR-003's
ownership assignment is otherwise unchanged and its text is preserved as a
historical record (the ADR-011/015/016 precedent). It **extends** ADR-012
(erasure is an outbox projection) and ADR-015 (the payload store gains an erase
operation); neither is superseded.

---

## Supersedes

None
