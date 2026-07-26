---
title: RFC-004 Audit Lifecycle and Durable Sink
status: Accepted
date: 2026-07-26
decision-makers: SentinelAI Team
---

# RFC-004: Audit Lifecycle and Durable Sink

> Single-page RFC per ADR-014 §2. Required because the proposal **amends the
> realization of an accepted architectural capability** — audit-and-observability.md
> §4/§7 declares audit records tamper-resistant, non-repudiable and complete, and
> this fixes what those words concretely oblige — and it **introduces a new
> authoritative store owner** (the audit log) with its own retention model,
> touching ADR-003's ownership map — ADR-014 thresholds (a) and (c).

## Status

**Accepted** (self-review per ADR-014 §3: evaluated against the design
principles and the Architecture Testing constraint catalogue; rationale below).

---

## Problem

audit-and-observability.md fixes the audit **model**: what is auditable (§4),
that every record must be *attributable, chronological, tamper-resistant,
non-repudiable and complete* (§4), and that audit integrity must survive
independently of the component that produced the event (§7). Nothing in the
platform makes those adjectives true. The only recorder is
`LoggingAuditRecorder` (ES-021), which writes a line to a log stream: it is not
append-only (a log can be truncated or rotated away), carries no integrity
evidence (an edited line is indistinguishable from an original), has no
retention model, and disappears with the container.

Three consequences follow. First, the platform cannot answer "who erased this
investigation?" after a log rotation — while data-lifecycle.md §5 requires
exactly that record to survive the erasure it documents. Second, the audit
**vocabulary** is three actions wide (`operation.performed`,
`authentication.failed`, `authorization.denied`), so the Investigation,
Administrative and System categories §4 declares are unrepresentable, and ES-064
had to record an erasure as an ordinary "operation performed". Third, the
document is Draft and the **audit lifecycle is an open documentation gap** — who
owns the sink, how long records live, what integrity guarantee is actually
claimed — so no implementation could be written without inventing that policy in
code, which the standing rule forbids.

---

## Proposed Change

Admit an **audit lifecycle** — ownership, integrity model, retention and
vocabulary — and realize it as a durable sink behind the existing
`AuditRecorder` port.

- **The Platform owns the audit log as an authoritative store.** Audit records
  are not derived from anything: they are the primary record of what happened,
  so they are authoritative, owned by the Platform rather than by any business
  service, and stored in the authoritative store technology (PostgreSQL,
  ADR-003). No business service reads or writes them; the audit capability is
  reached only through the `AuditRecorder` port.
- **Append-only is a property of the record, not a hope about callers.** An
  audit record is written once and never updated or deleted by the platform.
  The only sanctioned removal is retention expiry (below), which removes whole
  records from the *oldest* end and never edits one.
- **Tamper-evidence by hash chain.** Each record carries the digest of the
  previous record and a digest over its own canonical content. Any alteration,
  removal or reordering of a record breaks the chain from that point on, so
  integrity is **verifiable** rather than asserted. This is the concrete
  realization of §4 "tamper-resistant" and §7 "audit integrity should remain
  independent of the component that produced the event": verification needs only
  the records themselves.
- **Non-repudiation is bounded to chain integrity for 1.0.** The chain proves
  that the stored sequence has not been altered *since it was written*. It does
  not prove authorship to a third party — that needs signing keys or external
  notarization, which are deployment concerns with their own key lifecycle.
  Recording the bound explicitly is part of the decision: a claim of
  non-repudiation the platform cannot support would be worse than a narrower
  claim it can.
- **Retention is deployment policy; the retention *path* is architecture.**
  Consistent with data-lifecycle.md §3, the audit sink declares a retention
  duration as configuration and exposes an expiry operation; how long a
  deployment keeps audit records is that deployment's legal decision.
- **Audit records survive the erasure they document** (data-lifecycle.md §5).
  They are outside the erasure cascade. This is safe *because* audit records
  carry identifiers, not content: subject, operation, resource identifier and
  outcome — never investigation titles, evidence bodies or knowledge text. The
  audit exception costs the platform no additional personal data.
- **A vocabulary wide enough for the model.** The action vocabulary stays a
  closed enumeration but covers the §4 categories the platform acts in, so an
  erasure is recorded as an erasure rather than as an anonymous "operation
  performed". It carries no value that nothing emits: the *administrative*
  category stays unrepresented until an administrative surface exists, because a
  placeholder would assert accountability the platform cannot deliver.
- **Audit never fails the operation it documents.** A sink failure is contained
  and reported (ES-021 stance) — but it must be *loud*: an unrecorded action is
  an accountability gap, so a write failure is both counted as an operational
  signal and still emitted to the log sink, so the event is degraded rather
  than lost.

## Affected ADRs / Constraints

- **ADR-003 (amended, via ADR-018):** the ownership map gains the audit log — a
  Platform-owned authoritative category in PostgreSQL. ADR-003's text is
  preserved (the ADR-011/015/016/017 precedent).
- **ADR-017 / data-lifecycle.md §5 (realized):** the audit exception becomes
  concrete — erasure operations are recorded with their own action category, and
  the record outlives the erased data.
- **AC-14 preserved:** the audit write is its own transaction against its own
  store, never joined to a business service's transaction, so no request path
  writes two stores. The business operation and its audit record are not
  atomic with each other **by design** — see the alternatives.
- **AC-04 preserved:** the recorder stays behind the application-layer port;
  the concrete store lives in infrastructure.
- **audit-and-observability.md moves Draft → Accepted**, closing the
  "Audit lifecycle specification" documentation gap.

## Scope Boundary (explicitly out)

- **Cryptographic signing / external notarization / write-once media** — the
  stronger non-repudiation schemes. Documented as the evolution path; not 1.0.
- **An audit query/export API.** The records are durable and verifiable; a
  surface for reading them is a separate capability with its own authorization
  model (who may read the audit log is not "whoever may call the API").
- **Automated retention enforcement** (a scheduled expiry sweep) rides with the
  retention sweeper for the other categories rather than being built twice.
- **Per-business-operation semantic audit inside services** (ES-021 TD): the
  boundary recorder still derives the action from the request. Services
  contributing their own richer events is a later refinement, and the widened
  vocabulary is what makes it possible.
- **AI Runtime audit contribution** (ES-021 TD): every AI step is already
  recorded in the Investigation Trace, which is the explainability journal for
  exactly that purpose. Duplicating it into the security audit would mix an
  investigation-scoped, erasable record with a retention-bound accountability
  record — the two have opposite lifecycles (data-lifecycle.md §5). The AI
  Runtime therefore contributes to audit only through the operations its
  callers perform.

## Alternatives Dismissed

- **Keep the log-only recorder and ship log shipping instead.** Moves the
  problem to infrastructure the platform does not own and cannot verify: a
  shipped log is still editable at rest, and "complete" becomes a property of
  someone's collector configuration rather than of the record.
- **Write the audit record inside the business transaction.** Tempting — it
  would make "operation happened" and "operation was audited" atomic. Rejected:
  it couples every business write to the audit store's availability, and an
  audit failure would then roll back the analyst's work, which inverts the
  ES-021 stance that audit must never take down the operation. It would also
  make the audit log a participant in business transactions, which is exactly
  the coupling ADR-004 avoids.
- **A separate audit database/service.** More isolation, but a second
  authoritative technology for one table, and a cross-process write on the
  request path. PostgreSQL is already the authoritative store; a distinct
  schema/table with no business foreign keys gives the isolation that matters.
- **Signed records for 1.0.** Requires a signing key with its own rotation,
  distribution and revocation lifecycle (secrets-management.md) — a larger
  surface than the guarantee justifies today, and the chain is a strict
  prerequisite for it anyway.
- **Making the chain a per-tenant sequence.** Would let one tenant's verification
  proceed independently, but multiplies chain heads and makes global ordering
  ambiguous. A single chain matches "chronological" (§4) and stays verifiable in
  one pass; per-tenant partitioning is a scale concern, recorded as evolution.

## Acceptance Criteria

- ADR-018 records the decision; audit-and-observability.md moves to Accepted
  with the lifecycle (owner, integrity model, retention, vocabulary,
  AI-Runtime position) specified; the documentation gap is closed.
- A durable recorder behind the `AuditRecorder` port appends records with a
  verifiable hash chain; verification detects alteration, removal and
  reordering.
- The action vocabulary covers the §4 categories, and erasure is recorded as
  an erasure.
- A sink failure never fails the audited operation, and is observable.
- Retention duration is configuration; the expiry path exists and never edits a
  record.
- All verification gates green; AC-14 holds (and is now mechanically enforced).
