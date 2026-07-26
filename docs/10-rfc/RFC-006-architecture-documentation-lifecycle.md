---
title: RFC-006 Architecture Documentation Lifecycle
status: Accepted
date: 2026-07-26
decision-makers: SentinelAI Team
---

# RFC-006: Architecture Documentation Lifecycle

> Single-page RFC per ADR-014 §2. Required because the proposal **amends
> ADR-014** (the governance process gains a document lifecycle alongside the
> proposal and decision lifecycles) and **adds an enforced architectural
> constraint** to the Architecture Testing catalogue (AC-16) — ADR-014
> thresholds (a) and (b).

## Status

**Accepted** (self-review per ADR-014 §3: evaluated against the design
principles and the Architecture Testing constraint catalogue; rationale below).

---

## Problem

SentinelAI is an architecture-first project: the `docs/` corpus is not
supporting material, it is the primary artifact the platform is built to
satisfy. That corpus cannot currently describe its own state.

**A document's status carries no information.** ADRs have a status vocabulary
with a normative meaning — "only *Accepted* decisions are considered part of the
active SentinelAI architecture" (ADR README) — and RFCs have a proposal
lifecycle (RFC Process §5). Architecture documents have neither. Forty of the
forty-two documents under `docs/` are marked `Draft`, including documents whose
content has been delivered, verified and live for weeks; two documents were
promoted to `Accepted` during ES-069/ES-070 by an unwritten rule. A reader
cannot distinguish "not yet reviewed", "aspirational", and "describes what the
platform does today", because all three are spelled the same way.

**The corpus is silent about what it does not decide.** The project keeps an
honest register of its deferrals — the tracker's *Open Documentation Gaps* and
*Deferred Decisions*, the backlog's deferred work — but those live in
maintainer-local files (`implementation/` is gitignored; `workdocs/` is
explicitly "not part of the project documentation"). The public documents
therefore read as complete specifications of an architecture that in several
places has deliberately not been decided: evidence detach semantics, report
lifecycle, Task service ownership, the canonical timeline event source and
others. A reader of the public corpus cannot see the boundary between what is
settled and what is deliberately open — and the gap register is invisible
exactly where a contributor would look for it.

**Freshness is enforced for one artifact and hoped for everywhere else.**
AC-15 makes one derivable artifact (`docs/api/openapi.json`) provably current,
and the pattern works. Nothing else is checked, and the drift is measurable
today: `database-architecture.md` declares version 1.2.0 while its own version
history reaches 1.4.0, `graph-service.md` declares 1.1.0 against a 1.2.0
history (both stale since 2026-07-23), `api-design.md` records its history rows
out of order, `system-overview.md` has no version history at all, the RFC
directory has no index while the ADR directory does, and three configuration
fields the platform actually reads are absent from `.env.example`. None of these
is severe on its own; together they are the observable failure mode of
governance that is asserted rather than verified.

---

## Proposed Change

Give architecture documents the same kind of lifecycle the project already
gives decisions, make deferrals public where they belong, and check
mechanically what is checkable.

- **Architecture documents carry a status from a defined vocabulary**:
  `Draft`, `Accepted`, `Superseded`, `Deprecated` — deliberately the ADR
  vocabulary minus `Proposed` (a document is not a proposal; that is what an
  RFC is for).
- **The promotion rule is explicit.** A document is `Accepted` when every
  normative statement it makes is either **realized in the platform** or
  **explicitly bounded within the document itself**. Anything else stays
  `Draft`. Promotion is a claim about the document's honesty, not about the
  platform's completeness: a document describing a capability the platform has
  deliberately not built can be `Accepted` once it says so.
- **Known gaps are recorded publicly, in the document that owns them.** An
  architecture document that leaves a question open carries a **Known Gaps**
  section naming the gap, what the platform does today instead, and the
  governance path that would close it (documentation, ADR, or RFC per the
  ADR-014 threshold). The maintainer's private registers remain the working
  index; the public corpus stops implying completeness it does not have.
- **Governance artifacts are machine-checked (AC-16)** wherever correctness is
  derivable — the AC-15 pattern generalized: front matter completeness and an
  allowed status value; front matter consistent with the document's own version
  history; ADR and RFC indexes complete in both directions; no reference to a
  decision or proposal that does not exist; every constraint the catalogue
  records as *Enforced* naming a verification that exists; and every
  configuration field the platform reads documented in the configuration
  example.
- **What is not derivable is not checked.** Whether a document's prose is
  accurate, complete or well-written stays a review responsibility. AC-16 exists
  to make *silent* drift impossible, not to simulate review.

## Affected ADRs / Constraints

- **ADR-020 (new):** records the document lifecycle, the promotion rule, the
  known-gap obligation and AC-16.
- **ADR-014 (amended, additively):** the governance model gains a third
  lifecycle — proposals (RFC), decisions (ADR) and now documents. No threshold,
  form or review rule changes.
- **architecture-testing.md (amended):** AC-16 added to the normative constraint
  catalogue as *Enforced*; the catalogue remains the authoritative source of
  concrete constraints.
- **docs/09-decisions/README.md, docs/10-rfc/README.md (amended):** the ADR
  index gains the completeness obligation it already satisfies informally; the
  RFC directory gains the index it lacks.
- **AC-15 preserved and generalized:** the contract-freshness constraint is the
  precedent, unchanged; AC-16 covers the remaining derivable artifacts.

## Scope Boundary (explicitly out)

- **Documentation quality gates** — prose linting, readability metrics, link
  checking against external URLs, spell checking. Not derivable from the
  architecture, and noise in a governance constraint destroys its authority.
- **A generated documentation site**, navigation or search. Presentation, not
  governance.
- **Resolving the open documentation gaps themselves.** This RFC makes them
  visible and assigns each a governance path; several are above the ADR-014
  threshold and must be decided on their own merits, not as a side effect of a
  documentation-lifecycle change.
- **Versioning policy for the platform and its public API** (what a release
  version means, what compatibility it promises). That is release governance and
  is decided separately.
- **Retroactive review of accepted decisions.** ADRs 001–019 are untouched;
  this RFC governs documents, not decisions.

## Alternatives Dismissed

- **Leave every document `Draft` until Release 1.0, then promote all of them.**
  A single bulk promotion is a rubber stamp: it asserts that forty documents are
  simultaneously honest without ever having applied a rule to any of them, and
  it leaves the corpus uninformative for the entire pre-release period — which
  is exactly when a contributor needs to know what is settled.
- **Drop the status field from architecture documents.** Honest about the
  current state, and it discards the one place a reader could learn whether a
  specification is live. It also diverges from ADR/RFC governance for no reason
  other than the field being unused.
- **Keep the gap register private and link to it.** `implementation/` is
  gitignored and `workdocs/` is declared not to be project documentation; a
  public link to a private file is worse than no link. Recording the gap in the
  owning document also puts it where the reader who cares is already reading.
- **One central `known-gaps.md` document.** Simpler to write, and it violates
  the project's explicit-ownership principle — the gap would live outside the
  document that owns the concept, and would drift from it exactly as the private
  registers already do.
- **Enforce freshness through review discipline rather than tests.** This is the
  status quo, and it produced two stale front matters, an unordered history, a
  missing history table, a missing index and three undocumented settings fields
  — all in a project with an unusually disciplined maintainer. Review does not
  scale to mechanical invariants.
- **Check documentation freshness in CI only (a workflow step, not a test).**
  It would run in CI but not on the maintainer's machine, inverting the
  project's gate model where `pytest` is the verification everything else
  mirrors.

## Acceptance Criteria

- ADR-020 records the decision; the ADR and RFC indexes list every decision and
  proposal, and both are reachable from their directory README.
- Every document under `docs/` carries valid front matter with a status from the
  defined vocabulary, and its front matter agrees with its own version history.
- Every document left `Draft` states why; every document promoted to `Accepted`
  either makes no unrealized claim or carries a Known Gaps section that bounds
  the ones it makes.
- The still-open documentation gaps are stated in the documents that own them,
  each with its Release 1.0 disposition and governance path.
- AC-16 is recorded in the constraint catalogue as *Enforced* and is verified by
  the default test suite; the drift it detects today is fixed rather than
  waived.
- All verification gates green.
