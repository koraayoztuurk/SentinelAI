# Architecture Decision Records (ADRs)

## Purpose

This directory contains the Architecture Decision Records (ADRs) for SentinelAI.

Each ADR captures a significant architectural decision together with its context, rationale and long-term consequences.

Unlike architecture documents, ADRs explain **why** a decision was made rather than **how** the system is implemented.

Architecture documents describe the platform.

ADRs document the reasoning behind the architecture.

---

# Why ADRs?

Architectural decisions become increasingly difficult to revisit as a system evolves.

Recording important decisions provides:

- architectural consistency
- historical context
- transparent and traceable decision making
- easier onboarding
- improved maintainability

Future contributors should consult the ADRs before proposing architectural changes.

---

# ADR Structure

Each ADR follows a consistent structure.

## Status

Indicates the current state of the decision.

Possible values include:

- Proposed
- Accepted
- Superseded
- Deprecated

Only **Accepted** decisions are considered part of the active SentinelAI architecture.

---

## Context

Describes the architectural problem that required a decision.

The Context should explain:

- what problem existed
- why it mattered
- what constraints influenced the decision

---

## Decision

Describes the architectural decision itself.

This section records the chosen solution without discussing implementation details.

---

## Rationale

Explains why the selected decision was preferred.

The rationale should describe the engineering principles that motivated the decision.

**Rationale must be decision-specific.** Generic quality attributes ("improves maintainability, scalability and ownership") apply to almost any decision and therefore justify none; they may appear only in support of decision-specific drivers. A rationale should answer, concretely for this decision:

- which problem or constraint drove it (traceable to the Context)
- what would go wrong under the rejected alternatives, specifically
- how the decision's success or violation can be observed or verified (a measurable or checkable consequence — for example an enforceable constraint, a testable boundary or an explicit ownership rule)

New ADRs (ADR-010 onward) are expected to meet this standard; earlier ADRs are historical records and are not rewritten retroactively.

---

## Alternatives Considered

Every important architectural decision should evaluate reasonable alternatives.

Rejected alternatives provide historical context and reduce repeated architectural discussions.

---

## Consequences

Documents the impact of the decision.

Consequences are divided into:

- Positive
- Negative
- Trade-Offs

Every architectural decision introduces both benefits and costs.

---

## Related Documents

Lists architecture documents that elaborate on the decision.

Architecture documents provide implementation guidance.

ADRs provide architectural justification.

---

## Notes

Optional section for additional observations, future considerations or architectural constraints.

---

## Supersedes

Indicates whether the ADR replaces a previous decision.

If no previous decision exists, the value should be:

```
None
```

---

# Modification Policy

Accepted ADRs represent approved architectural decisions.

They should not be modified casually.

If a decision changes significantly, a new ADR should normally be created.

Previous decisions should remain available for historical reference.

---

# Relationship with Architecture Documents

SentinelAI distinguishes between architecture documentation and architectural decisions.

| Architecture Documents | ADRs |
|------------------------|------|
| Describe the architecture | Explain architectural decisions |
| Focus on responsibilities | Focus on reasoning |
| May evolve frequently | Expected to remain stable |
| Explain how the system works | Explain why the system was designed this way |

Both document types are required to fully understand the platform.

---

# Relationship with RFCs

Architectural proposals are governed through the RFC Process.

Accepted architectural proposals normally result in one or more Architectural Decision Records (ADRs).

The RFC Process governs:

- architectural proposals
- proposal review
- proposal lifecycle
- governance decisions

ADRs record the accepted architectural decisions resulting from that governance process.

RFCs and ADRs serve complementary governance responsibilities.

RFCs should never replace ADRs, and ADRs should never replace the RFC Process.

---

# Current ADRs

| ADR | Decision |
|------|----------|
| ADR-001 | Overall System Architecture |
| ADR-002 | Multi-Agent Architecture |
| ADR-003 | Polyglot Persistence |
| ADR-004 | Backend Service Boundaries |
| ADR-005 | AI Runtime Architecture |
| ADR-006 | Retrieval-Augmented Generation (RAG) |
| ADR-007 | ThreatGraph Architecture |
| ADR-008 | API Architecture |
| ADR-009 | Frontend Architecture |
| ADR-010 | Planner Composition and AI Orchestration Ownership |
| ADR-011 | Supporting Persistence Technologies |
| ADR-012 | Derived Representation Production and Propagation |
| ADR-013 | AI Provider Resilience and the Single Agent Execution Path |
| ADR-014 | Lightweight Architectural Proposal Process |
| ADR-015 | Evidence Payload Store |

---

# Contributing

Before introducing a significant architectural change:

1. Review the existing ADRs.

2. Verify that the proposed change does not conflict with accepted architectural decisions.

3. Create or update an RFC describing the proposed architectural change.

4. Complete the RFC review process.

5. If the RFC is accepted, create one or more ADRs documenting the accepted architectural decision.

6. Supersede previous ADRs rather than silently modifying them.

The RFC Process is the canonical governance mechanism for proposing architectural evolution.

ADRs remain the canonical record of accepted architectural decisions.

Architectural consistency is preferred over short-term implementation convenience.