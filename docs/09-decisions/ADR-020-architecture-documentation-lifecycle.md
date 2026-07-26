---
title: ADR-020 Architecture Documentation Lifecycle
status: Accepted
date: 2026-07-26
decision-makers: SentinelAI Team
---

# ADR-020: Architecture Documentation Lifecycle

## Status

**Accepted** (proposed and reviewed through RFC-006, under ADR-014).

---

## Context

SentinelAI governs its decisions (ADR status vocabulary, where only *Accepted*
is part of the active architecture) and its proposals (RFC lifecycle). It does
not govern its **documents**, although in an architecture-first project the
document corpus is the primary artifact.

The consequences were concrete at the end of Milestone G: forty of forty-two
documents under `docs/` were marked `Draft` — including documents whose content
had been delivered and running for weeks — while two had been promoted to
`Accepted` by an unwritten rule, so the field carried no information. The
project's honest register of deferrals lived only in maintainer-local files
(`implementation/` is gitignored, `workdocs/` is declared not to be project
documentation), leaving the public corpus reading as a complete specification of
an architecture that in several places was deliberately undecided. And exactly
one derivable artifact was mechanically kept current (`openapi.json`, AC-15),
while measurable drift accumulated elsewhere: two documents whose front matter
had fallen behind their own version history, one with its history rows out of
order, one with no history table, an RFC directory with no index, and three
configuration fields the platform reads but the configuration example never
mentions.

RFC-006 proposed a document lifecycle, a public known-gap obligation and a
generalization of the AC-15 pattern; this ADR records the decision.

---

## Decision

### 1. Architecture documents carry a status from a defined vocabulary

`Draft`, `Accepted`, `Superseded`, `Deprecated` — the ADR vocabulary without
`Proposed`, because a document is not a proposal (an RFC is). The status is
declared in the document's front matter and means the same thing in every
document.

### 2. A document is Accepted when every normative statement it makes is realized or bounded

Promotion is a claim about the **document's honesty**, not about the platform's
completeness. A document may describe a capability the platform has deliberately
not built and still be `Accepted` — provided the document says so. If any
normative statement is neither realized nor explicitly bounded within the
document, the document stays `Draft`, and the reason is stated.

### 3. Known gaps are recorded publicly, in the document that owns them

An architecture document that leaves a question open carries a **Known Gaps**
section naming the gap, what the platform does today in its place, and the
governance path that would close it (documentation, ADR, or RFC per the ADR-014
threshold). Maintainer-local registers remain the working index; they stop being
the *only* place the boundary between decided and undecided is visible.

### 4. Governance artifacts are machine-checked where correctness is derivable (AC-16)

The AC-15 pattern is generalized into one constraint covering front-matter
validity, front matter agreeing with the document's own version history, ADR and
RFC index completeness in both directions, references that resolve to existing
decisions and proposals, every constraint recorded *Enforced* naming a
verification that exists, and every configuration field the platform reads being
documented in the configuration example.

### 5. What is not derivable is not checked

Accuracy, completeness and clarity of prose remain review responsibilities.
AC-16 exists to make *silent* drift impossible, not to simulate review; checks
that would fire on style or taste are excluded by design.

---

## Rationale

- The status field either means something or it should not exist. Making it mean
  something — with a stated promotion rule — turns forty documents from
  undifferentiated `Draft` into a corpus that reports which architecture is
  active, which is the same service ADR statuses already provide for decisions.
- Honesty is verifiable where completeness is not. "Every claim is realized or
  bounded" is a rule a reviewer can actually apply to a document, whereas "the
  documentation is complete" is unfalsifiable and would make promotion
  meaningless.
- A gap recorded in the owning document is the explicit-ownership principle
  applied to documentation: the concept and its open question live in one place
  and drift together or not at all.
- AC-15 is the precedent and the proof: a derivable artifact with a test stopped
  drifting, while everything relying on review discipline drifted — in a
  single-maintainer project with an unusually disciplined maintainer. The
  mechanism, not the diligence, is what made the difference.
- The constraint is checkable and its scope is bounded: every AC-16 rule fails
  on a fact (a missing field, a mismatched version, an unindexed file, an
  undocumented setting), never on a judgement.

---

## Alternatives Considered

See RFC-006 (bulk promotion at release; dropping the status field; keeping the
gap register private; a single central gap document; review discipline instead
of tests; CI-only enforcement) — all dismissed there with rationale.

---

## Consequences

### Positive

- A reader can tell, per document, whether it describes the live architecture,
  and where it deliberately stops.
- The public corpus states its own boundaries, so a contributor sees the open
  questions in the document that owns them rather than inferring completeness.
- Documentation drift becomes a failing test on the maintainer's machine and in
  CI, at the same moment it is introduced.
- Future governance artifacts inherit the pattern: an index, a status and a
  check, rather than a convention.

### Negative

- Every document change now carries a small mechanical obligation (front matter,
  version history, and — where a document is promoted — an honest gap
  statement). This is the intended cost.
- `Accepted` documents will need re-review when the platform changes underneath
  them; a stale `Accepted` is a worse failure than a stale `Draft`, because it
  asserts something. AC-16 cannot detect it — only the version-history
  obligation makes the change visible.
- The promotion rule requires a judgement call per document, and a document
  promoted too eagerly devalues the vocabulary for all the others.

### Trade-Offs

Mechanical checks are deliberately narrow: they verify that governance artifacts
are *consistent and complete*, not that they are *correct*. This accepts that a
thoroughly wrong document can pass AC-16, in exchange for a constraint that
never fires spuriously and therefore stays trusted.

---

## Related Documents

- RFC-006 Architecture Documentation Lifecycle
- ADR-014 Lightweight Architectural Proposal Process (the governance model this
  extends additively)
- Architecture Testing (Constraint Catalogue — AC-15 precedent, AC-16 declared
  and enforced)
- API Design §14a Contract Synchronization (the committed-artifact + freshness
  pattern being generalized)
- ADR README (ADR status vocabulary and index), RFC Process (proposal lifecycle
  and index)

---

## Notes

This ADR **extends** ADR-014 additively: the RFC threshold, the single-page form
and the self-review rule are unchanged; governance simply gains a third
lifecycle alongside proposals and decisions. No existing ADR is superseded, and
no document's content is altered by this decision — only its declared state and,
where a gap exists, its explicit statement of that gap.

---

## Supersedes

None
