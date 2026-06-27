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
- transparent decision making
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

---

# Contributing

Before introducing a significant architectural change:

1. Review the existing ADRs.
2. Verify that the proposed change does not conflict with accepted decisions.
3. Create a new ADR if a new architectural decision is required.
4. Supersede previous ADRs instead of silently modifying them.

Architectural consistency is preferred over short-term implementation convenience.