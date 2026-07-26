---
title: ADR-018 Audit Lifecycle and Durable Sink
status: Accepted
date: 2026-07-26
decision-makers: SentinelAI Team
---

# ADR-018: Audit Lifecycle and Durable Sink

## Status

**Accepted** (proposed and reviewed through RFC-004, under ADR-014).

---

## Context

audit-and-observability.md §4 requires every audit record to be attributable,
chronological, **tamper-resistant**, **non-repudiable** and **complete**, and §7
requires audit integrity to hold independently of the component that produced
the event. The platform's only recorder writes a log line (ES-021): not
append-only, carrying no integrity evidence, with no retention model, lost with
the container. The audit **lifecycle** — who owns the sink, how long records
live, what integrity guarantee is actually claimed, what vocabulary the records
use — was an open documentation gap, so the durable sink could not be built
without inventing policy in code. RFC-004 proposed admitting the lifecycle and
realizing it behind the existing port; this ADR records the accepted decision.

---

## Decision

### 1. The audit log is a Platform-owned authoritative store

Audit records are the primary record of what happened — derived from nothing, so
authoritative by definition. They are owned by the **Platform**, not by any
business service, and live in the authoritative store technology (PostgreSQL,
ADR-003) in their own table with **no foreign keys to business data**: the audit
log outlives what it describes (§5 audit exception), so a referential dependency
on erasable rows would be a contradiction.

No business service reads or writes audit records. The capability is reached
only through the application-layer `AuditRecorder` port (ES-021), whose boundary
is unchanged — the durable sink is a **new adapter**, not a new contract.

### 2. Append-only, with retention expiry as the only removal

An audit record is written once. The platform never updates one and never
deletes an individual one. The single sanctioned removal is **retention
expiry**, which removes whole records from the oldest end of the chain and never
alters a retained record's content.

### 3. Tamper-evidence is a hash chain over the record sequence

Each record carries:

- a digest over its own canonical content, and
- the digest of the record before it.

Altering, removing or reordering any record breaks every digest after it, so
integrity is **verifiable from the records alone** — no external ledger, no
trust in the process that wrote them. This realizes §4 "tamper-resistant" and
§7 "independent of the producing component" concretely.

The chain is **single and global**, not per-tenant: §4 requires records to be
chronological, and one chain gives one unambiguous order that verifies in a
single pass.

### 4. Non-repudiation is bounded to chain integrity for 1.0

The chain proves the stored sequence has not been altered since it was written.
It does **not** prove authorship to a third party — that requires signing keys
or external notarization, each with its own key lifecycle
(secrets-management.md). The bound is recorded deliberately: a stronger claim
than the platform can support would itself be an accountability failure.
Signing, external notarization and write-once media are the documented
evolution path.

### 5. Retention duration is deployment policy; the retention path is architecture

Consistent with data-lifecycle.md §3, **how long** audit records are kept is a
deployment's legal decision, expressed as configuration. That an expiry path
**exists**, that it removes only whole expired records, and that it never edits
a retained one, is architecture.

### 6. Audit records survive the erasure they document

Audit records are outside the erasure cascade (data-lifecycle.md §5, ADR-017).
This is safe because of what an audit record contains: **identifiers, not
content** — subject, identity kind, operation, affected resource identifier,
outcome, request id, timestamp. No investigation title, evidence body or
knowledge text ever enters an audit record, so the audit exception costs the
platform no retained personal content beyond the subject identifier that
accountability itself requires.

### 7. A closed vocabulary, one value per activity the platform can actually perform

The action vocabulary remains a **closed** enumeration (type-safe, reviewable)
and covers the §4 categories the platform acts in — identity, authorization,
investigation and system activities — so an erasure is recorded as an erasure
rather than as an anonymous "operation performed" (the ES-064 deferral).

It deliberately carries **no value that nothing emits**. The §4
*administrative* category has no vocabulary entry because the platform exposes
no administrative surface; a placeholder value would assert an accountability
capability that does not exist. Adding a value is a documentation decision taken
when the activity it names becomes real, not an incidental code change.

### 8. Audit never fails the operation it documents, and never fails silently

A sink failure is contained: the audited operation still succeeds (the ES-021
stance — audit must not take down the platform it observes). But an unrecorded
action is an accountability gap, so a failure is **loud**: it is counted as an
operational signal *and* the event is still emitted to the log sink, so the
record is degraded rather than lost.

### 9. The audit write is its own transaction

The audit record is written in a transaction of its own, never joined to a
business service's transaction. The business operation and its audit record are
therefore **not atomic with each other** — an accepted trade (see Consequences),
and the reason AC-14 is preserved: no request path writes two stores.

---

## Rationale

- audit-and-observability.md already fixed the model; this decides only what its
  adjectives concretely oblige, which is what the documentation gap asked for.
- A hash chain is the smallest mechanism that turns "tamper-resistant" from an
  assertion into a **check**, and it is a prerequisite for every stronger scheme,
  so nothing is wasted by starting there.
- Keeping audit records to identifiers rather than content is what makes the
  §5 audit exception defensible: retention and erasure obligations stop
  competing when the retained record holds no content to erase.
- A separate transaction keeps the availability of the audit store off the
  business write path — audit observes the platform; it must not be able to stop
  it.
- Reusing the ES-021 port means the boundary that was designed for this arrives
  unchanged: the sink is a swap at the composition root.

---

## Alternatives Considered

See RFC-004 (log-only + log shipping; audit inside the business transaction; a
separate audit database/service; signed records for 1.0; per-tenant chains) —
all dismissed there with rationale.

---

## Consequences

### Positive

- "Who did what, when, with what outcome" survives log rotation, container
  restarts and the erasure of the data it describes.
- Integrity is verifiable rather than asserted; a tampered or truncated audit
  log is **detectable**.
- Erasure operations are recorded as erasures, closing the ES-064 deferral and
  making data-lifecycle.md §5 real.
- The audit capability gained no new boundary: the ES-021 port and the
  best-effort containment stance both stand.

### Negative

- The business operation and its audit record are not atomic: a crash between
  them can leave an operation performed but unrecorded. The window is small and
  the failure is observable, but it is real — the alternative (atomicity) was
  rejected because it lets the audit store fail business work.
- Chain verification is O(n) over the retained records; at large volumes it
  becomes a periodic job rather than an on-demand check.
- Retention expiry necessarily truncates the chain's tail; verification is
  therefore over the *retained* sequence, and the expiry boundary must be
  recognized rather than reported as tampering.
- A single global chain serializes appends; per-tenant partitioning is the
  documented scale path.

### Trade-Offs

A small non-atomicity window between an operation and its audit record is
accepted in exchange for audit never being able to fail the operation it
observes — the same containment stance ES-021 took, now made explicit as a
decision rather than an implementation detail.

---

## Related Documents

- RFC-004 Audit Lifecycle and Durable Sink
- Audit and Observability (§4 audit model and characteristics, §6 audit
  responsibilities, §7 audit integrity — moved to Accepted with the lifecycle
  specified)
- Data Lifecycle and Erasure (§3 retention as policy, §5 audit exception)
- Security Architecture (accountability)
- Secrets Management (why signing is deferred: key lifecycle)
- ADR-003 Polyglot Persistence (amended: the ownership map gains the
  Platform-owned audit log)
- ADR-017 Data Erasure and Tombstoning (the audit exception it relies on)

---

## Notes

This ADR **amends ADR-003** by adding the Platform-owned audit log to the
ownership map; ADR-003's business-data ownership assignment is unchanged and its
text is preserved as a historical record (the ADR-011/015/016/017 precedent). It
**realizes** data-lifecycle.md §5 rather than changing it. No ADR is superseded.

---

## Supersedes

None
