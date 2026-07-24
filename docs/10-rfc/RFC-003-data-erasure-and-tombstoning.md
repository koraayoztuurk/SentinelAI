---
title: RFC-003 Data Erasure and Tombstoning
status: Accepted
date: 2026-07-23
decision-makers: SentinelAI Team
---

# RFC-003: Data Erasure and Tombstoning

> Single-page RFC per ADR-014 §2. Required because the proposal **amends an
> accepted ADR** (ADR-003's ownership model gains an end-of-life dimension) and
> **changes domain-model semantics** (a terminal erasure state + a cross-store
> tombstone protocol) — ADR-014 thresholds (a) and (c).

## Status

**Accepted** (self-review per ADR-014 §3: evaluated against the design
principles and the Architecture Testing constraint catalogue; rationale below).

---

## Problem

data-lifecycle.md (audit finding M-05) fixes the erasure **model** — lifecycle
ownership per category (§2), the principles that retention is policy while an
erasure path is architecture, that deprecation ≠ deletion, that erasing an
investigation erases its scoped objects, and that derived data is erased with
its source (§3) — and the two strategy categories, tombstoning and
crypto-shredding (§4). The document is status **Draft** and **no store has an
erasure path**: the Investigation family, Memory items, graph entities,
embeddings and evidence payloads can all be created but never ended. The
platform is preservation-first (immutable evidence, versioned memory,
append-only trace) with no way to satisfy a retention limit or a
right-to-be-forgotten request. Retrofitting erasure into an immutability-first
model later is the failure data-lifecycle.md §1 exists to prevent. No decision
record admits the erasure lifecycle.

---

## Proposed Change

Admit an **erasure lifecycle** across the owning services, with a uniform
**tombstone protocol** for cross-store references, realizing data-lifecycle.md.

- **Terminal erasure state.** Domain objects with a documented lifecycle gain a
  terminal `Erased` state. Erasure is orthogonal to the business lifecycle: any
  state may be erased; `Erased` is terminal — no business write or transition
  follows it. (domain-model.md §15 already reserves this: "removal is governed
  by the Data Lifecycle architecture", line 633.)
- **Tombstoning.** An erased record is replaced by an explicit erasure marker
  preserving **only non-personal correlation structure** — identifiers,
  timestamps (including the erasure timestamp), and the scope keys the
  authorization policy needs (owner, tenant) — and dropping personal content
  (§4). A tombstone is not a hidden or deleted row: a read resolves to an
  explicit "erased" state, never silently repaired, dropped or fabricated
  (database-architecture §8a).
- **Ownership-scoped cascade.** Erasing an investigation erases its
  investigation-scoped objects — evidence, findings, report, outcome, trace —
  all PostgreSQL-owned through the Investigation Service, tombstoned in one
  local transaction (§3, one operation = one store). Memory and the Knowledge
  Graph are §6a shared-knowledge layers: they are **not** cascaded by
  investigation erasure; they carry their own person-linked erasure path
  (right-to-be-forgotten), independent of any single investigation.
- **Secondary-store erasure is a projection.** Physical erasure of
  secondary-store bytes — embeddings in the vector store, raw payload bytes in
  the object store — propagates through the ADR-012 transactional outbox as an
  erasure projection (the same mechanism that produced them), never a
  synchronous second-store write inside the erasure operation. Erasure
  projections are idempotent and retriable like any other (ADR-012).
- **Per-store strategy is an adapter choice.** The *existence* of an erasure
  strategy per category is mandatory; *which* strategy is an adapter-level
  decision (§4). Tombstoning covers the record stores; the evidence payload
  store's designated strategy is crypto-shredding for the immutable production
  object store, with the dev-grade filesystem adapter erasing by physical
  deletion.
- **Erasure is audited.** Every erasure operation is a security-relevant action
  and is recorded through the existing audit boundary — who requested it, when
  (§5). Trace entries are investigation-scoped and follow the investigation's
  erasure; they are **not** part of the audit exception (§5).

## Affected ADRs / Constraints

- **ADR-003 (amended, via ADR-017):** the ownership model gains an end-of-life
  dimension — each owner now also owns its category's erasure path. Ownership
  assignment itself is unchanged; ADR-003's text is preserved (the
  ADR-011/015/016 precedent).
- **ADR-012 (extended):** erasure of derived/secondary-store representations is
  an outbox projection — the propagation mechanism ADR-012 defined is reused for
  end-of-life, not only for production.
- **ADR-015 (extended):** the `EvidencePayloadStore` port gains an erase
  operation; the accepted payload strategy is recorded in ADR-017.
- **Domain-model semantics:** a terminal `Erased` state and a redaction rule —
  the reason this needs an RFC (ADR-014 threshold c).
- **AC-14 preserved:** each erasure operation writes exactly one store; the
  investigation cascade is one PostgreSQL transaction; secondary-store erasure
  is asynchronous via the outbox. No request path writes two stores.
- **AC-07 preserved:** authorization for an erasure operation consults only the
  Investigation Service interface for the investigation's scope; the tombstone
  retains owner/tenant so post-erasure access decisions still resolve.

## Scope Boundary (explicitly out)

- **Automated retention enforcement** (a scheduled sweep that erases data past
  its retention policy) is out: this RFC admits the erasure *path*; retention
  *durations* are deployment policy (§3) and a background sweeper is a
  scheduled-job concern for Milestone G (the projector-hardening family).
- **Backup/restore interaction with erasure** is deferred until a backup
  architecture exists, so it is decided with it, not after it
  (data-lifecycle.md §6).
- **Legal interpretation** (mapping GDPR or other obligations to categories) is
  a deployment/compliance concern, not architecture (data-lifecycle.md §6).
- **A managed Tenant/subject-erasure orchestration** spanning every store from a
  single external request is out; each owning service exposes its category's
  erasure path (§2), invoked per category.

## Alternatives Dismissed

- **Hard delete (physical row removal) instead of tombstoning** — a reference to
  a hard-deleted object resolves to nothing, violating §8a "dangling references
  must remain observable"; the platform could not tell "never existed" from
  "erased", and audit/correlation structure would be lost.
- **Deprecation as erasure** — the Memory maturity model and entity deprecation
  control *relevance*, not *existence* (data-lifecycle.md §3); a deprecated item
  is still fully present. A deletion path must exist independently.
- **Synchronous multi-store erasure in one operation** — erasing PostgreSQL,
  the vector store and the object store together in one call is the dual-write
  ADR-012/AC-14 forbid: a mid-sequence failure diverges the stores with no
  recorded intent. The outbox records the erasure intent transactionally with
  the tombstone and lets idempotent projectors finish the job.
- **A single cross-service erasure component** — would centralize a
  responsibility ADR-004 distributes to owning services; each service owns its
  category's lifecycle end, consistent with how it owns its creation.

## Acceptance Criteria

- ADR-017 records the decision; data-lifecycle.md moves to Accepted and notes
  the realization; database-architecture §8a/§8b, domain-model.md §15 and
  api-design.md note the erasure surface.
- Erasing an investigation tombstones it and its scoped objects; reads resolve
  to an explicit erased state (never a silent 404-as-if-never-existed); the
  operation is owner+tenant scoped and audited; re-erasure is idempotent.
- Secondary-store bytes (embeddings, payloads) are erased through the outbox as
  an idempotent projection.
- All verification gates green; the one-store-per-operation constraint holds.
