---
title: ADR-007 ThreatGraph
status: Accepted
date: 2026-06-27
decision-makers: SentinelAI Team
---

# ADR-007: ThreatGraph Architecture

## Status

**Accepted**

---

## Context

SentinelAI uses graph-based knowledge to support cybersecurity investigations.

During the architectural design, a distinction was required between:

- representing graph knowledge
- utilizing graph knowledge during investigations

Combining these responsibilities into a single component would tightly couple data representation with investigation logic.

A dedicated abstraction was therefore required.

---

## Decision

SentinelAI distinguishes between the Knowledge Graph and ThreatGraph.

The Knowledge Graph represents persistent organizational knowledge.

ThreatGraph represents the investigation-oriented application layer that consumes graph knowledge to support AI-assisted investigations.

ThreatGraph is responsible for:

- graph exploration
- investigation context expansion
- attack path analysis
- relationship discovery
- graph reasoning support

ThreatGraph does not own graph persistence.

Graph persistence remains the responsibility of the Graph Service.

---

## Rationale

Separating graph representation from graph utilization provides:

- clearer architectural responsibilities
- improved maintainability
- reusable graph infrastructure
- independent evolution of graph capabilities
- better separation between storage and reasoning

ThreatGraph focuses on investigative workflows rather than graph storage.

---

## Alternatives Considered

### Knowledge Graph Only

Using the Knowledge Graph directly for every investigation capability was considered.

This approach tightly couples investigation workflows to graph representation and limits future evolution.

**Decision:** Rejected.

---

### Graph Database as Application Layer

Treating the graph database itself as the application layer was considered.

This exposes storage concerns to higher architectural layers and violates separation of responsibilities.

**Decision:** Rejected.

---

### Investigation Logic Inside Graph Service

Embedding investigation-specific graph reasoning within the Graph Service was considered.

This mixes business reasoning with persistence responsibilities and reduces service cohesion.

**Decision:** Rejected.

---

## Consequences

### Positive

- Clear separation between graph storage and graph utilization.
- Improved modularity.
- Better architectural consistency.
- Independent evolution of graph capabilities.
- Simplified maintenance.

---

### Negative

- Additional architectural abstraction.
- More coordination between components.
- Additional documentation required.

---

### Trade-Offs

The architecture introduces an additional abstraction layer to preserve long-term maintainability and clear responsibility boundaries.

---

## Related Documents

- Knowledge Graph
- ThreatGraph
- Graph Service
- AI Runtime
- Planner Agent

---

## Notes

ThreatGraph consumes graph knowledge but never owns it.

Graph persistence, validation and storage remain outside ThreatGraph.

Future graph reasoning capabilities should extend ThreatGraph without changing the ownership model established by this decision.

---

## Supersedes

None    