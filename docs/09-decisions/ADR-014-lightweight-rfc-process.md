---
title: ADR-014 Lightweight Architectural Proposal Process
status: Accepted
date: 2026-07-03
decision-makers: SentinelAI Team
---

# ADR-014: Lightweight Architectural Proposal Process

## Status

**Accepted**

---

## Context

The governance model defines a full RFC process (`docs/10-rfc/README.md`) and the Project Charter (§14) states that major architectural changes should begin with an RFC. In practice, the process has **never been exercised**: thirteen ADRs exist and zero RFCs — every architectural decision, including recent ones, was taken directly through an ADR.

A documented process that is never used erodes the governance claim it exists to support, and leaves "which change requires an RFC" undefined. The gap analysis (M-06/D-04) required an explicit choice: operate the process as written, or reshape it to the project's actual capacity (currently a single maintainer).

---

## Decision

### 1. The RFC requirement is scoped by an explicit threshold

An **RFC is required** only for proposals that:

- supersede or amend an accepted ADR,
- change a layer boundary or an enforced architectural constraint (Architecture Testing catalogue),
- change domain-model semantics (objects, lifecycles, ownership), or
- introduce a new backend service or a new persistence technology category.

All other architectural decisions proceed **directly as an ADR**, using the ADR's own `Proposed → Accepted` status transition as the discussion stage.

### 2. The RFC format is a single page

A conforming RFC states: the problem, the proposed change, the affected ADRs/constraints, the alternatives dismissed, and the acceptance criteria. The full lifecycle machinery in the RFC Process document is reduced to `Proposed → Accepted / Rejected` with a recorded rationale.

### 3. Self-review is legitimate at current capacity

With a single maintainer, review means a written, recorded evaluation against the design principles and the constraint catalogue — not a second person. The process scales up (real reviewers, discussion windows) without structural change when contributors exist.

### 4. Retroactivity

Existing ADRs (001–013) remain valid; none is reopened for lacking an RFC. This ADR itself falls under the threshold (it amends the governance process) and records its own rationale in lieu of the process it establishes.

---

## Rationale

- A threshold makes the RFC meaningful precisely where irreversibility is highest (superseding decisions, boundary changes) instead of demanding ceremony everywhere and receiving it nowhere.
- The observed decision flow (ADR-first) is formalized rather than prohibited — governance now describes reality, closing the "aspirational process" gap identified by the audit rather than re-asserting it.
- Verifiability: conformance is checkable — any future ADR that supersedes/amends another or changes an enforced constraint must reference its RFC; its absence is a visible governance violation.

---

## Alternatives Considered

### Operating the full RFC process as written

Requiring RFCs for all major changes with the complete lifecycle.

Thirteen decisions of evidence show this does not happen at current capacity; keeping the requirement guarantees continued non-compliance.

**Decision:** Rejected.

---

### Retiring the RFC layer entirely

Folding everything into ADR `Proposed → Accepted`.

This removes the one place where high-irreversibility changes get a structured pause; the threshold preserves that at near-zero cost.

**Decision:** Rejected.

---

## Consequences

### Positive

- Governance documentation matches governance practice.
- High-impact changes retain a mandatory, structured proposal step.
- The process is operable today and scales with the team.

### Negative

- Threshold judgment calls are possible at the margins (mitigated by listing concrete triggers).

### Trade-Offs

Ceremony is exchanged for a small, enforced core of governance where it matters most.

---

## Related Documents

- RFC Process (`docs/10-rfc/README.md`)
- Project Charter (§14 Architecture First)
- ADR README (Rationale standard)

---

## Notes

This ADR resolves audit findings **M-06** and **D-04**. The RFC Process document is updated to carry the threshold and the single-page format; the Charter's §14 statement remains true under the new scoping ("major" is now defined).

---

## Supersedes

None
