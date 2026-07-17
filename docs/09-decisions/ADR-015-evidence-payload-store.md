---
title: ADR-015 Evidence Payload Store
status: Accepted
date: 2026-07-17
decision-makers: SentinelAI Team
---

# ADR-015: Evidence Payload Store

## Status

**Accepted** (proposed and reviewed through RFC-001, the first exercised RFC
under ADR-014).

---

## Context

Database Architecture §8b fixes the target: raw evidence payloads live in a
content-addressed object store; the Evidence record references its payload by
content address (the integrity hash, Domain Rule 1/9); payloads are immutable;
payload access is mediated by the Investigation Service. It also requires an
explicit decision before the storage technology is introduced. RFC-001
proposed that admission; this ADR records the accepted decision.

---

## Decision

### 1. A content-addressed payload store joins the primary storage set

The store owns exactly one artifact kind: **raw evidence payload bytes**. It
is authoritative for those bytes (they are not reproducible from any other
store) and for nothing else. Every other ownership assignment of ADR-003
stands unchanged.

### 2. The address scheme is owned by the application

A payload's address is `sha256:<64 lowercase hex>` — the SHA-256 of its
bytes, computed by the **application layer** (Investigation package). The
address is a deterministic derivation from content, not a generated
identifier; adapters never mint addresses. The Evidence record's existing
`EvidenceIntegrity` value carries the address (§8b rule 1) — the domain model
is unchanged, and non-address integrity values (the inline-content interim)
remain valid.

### 3. Access is a minimal application port mediated by the Investigation Service

`EvidencePayloadStore` (application layer, Investigation package) exposes
exactly what the owning service needs: `put(address, content)` (idempotent —
re-storing existing content is a no-op), `get(address)` (`None` when
unresolvable — dangling references stay observable, §8a), `exists(address)`.
Only the Investigation Service consumes the port:

- **store** — requires the investigation to exist, computes the address,
  puts the payload; writes the object store only.
- **retrieve** — loads the Evidence record, fetches by its integrity value,
  **verifies the hash on read**; a missing payload and a hash mismatch are
  distinct stable errors, never silent repairs.
- **attach-time validation** — an evidence item whose integrity value is
  address-shaped (`sha256:` prefix) must reference an existing payload;
  non-address values are untouched (interim state preserved).

### 4. The first concrete adapter is a filesystem store (dev-grade)

A content-addressed directory layout under a configured root
(`EVIDENCE_PAYLOAD_ROOT`), atomic writes (temp file + rename), strict address
validation before any path construction (the address doubles as the
path-traversal guard). This is deliberately dev-grade and replaceable behind
the port — the dev-auth precedent. An S3-compatible object store is the
production path and belongs to Milestone G (production hardening).

### 5. Consistency and lifecycle boundaries

- **AC-14 preserved:** upload (object store) and attach (PostgreSQL) are
  separate single-store operations; content addressing makes upload
  idempotent and retry-safe. No request path writes two stores.
- **Orphaned payloads** (uploaded but never attached) are accepted;
  deletion, retention and erasure belong to data end-of-life (Milestone F,
  data-lifecycle.md — crypto-shredding applies to the payload store like any
  other store).
- **Format parsing / log normalization** stay outside this decision
  (investigation-service "Evidence Ingestion Boundary": a future capability
  requiring its own decision).

---

## Rationale

- §8b already fixed the target rules; this decision realizes them without
  inventing new semantics — the integrity value doubling as the content
  address is the documented design, not a new idea.
- Content addressing gives idempotence (safe retries, deduplication) and a
  verifiable integrity anchor in one mechanism.
- A minimal port with application-owned addressing keeps every platform
  discipline intact (minimal contracts, caller-supplied values, adapters as
  dumb edges).

---

## Alternatives Considered

See RFC-001 (inline payloads kept, supporting-persistence category, real
S3/MinIO deployment now) — all dismissed there with rationale.

---

## Consequences

### Positive

- Raw payloads become storable, referenceable and verifiable end to end.
- The authoritative record store stays lean; payload integrity is
  mechanically checkable on every read.
- The production object store becomes a pure adapter swap.

### Negative

- A filesystem store is single-node and quota-blind — explicitly dev-grade.
- Orphaned payloads accumulate until Milestone F defines end-of-life.

### Trade-Offs

Dev-grade storage now, real object store later — the platform accepts the
same interim/production split it already accepted for identity (dev token vs
production IdP).

---

## Related Documents

- RFC-001 Evidence Payload Object Store
- Database Architecture (§8b Evidence Payload Storage)
- Investigation Service (Evidence Ingestion Boundary)
- ADR-003 Polyglot Persistence (amended: ownership map extension)
- ADR-011 Supporting Persistence Technologies (category model)
- ADR-014 Lightweight Architectural Proposal Process

---

## Notes

This ADR **amends ADR-003** by adding a fourth primary storage technology
owning raw evidence payload bytes only; ADR-003's text is preserved as a
historical record (ADR-011 precedent).

---

## Supersedes

None
