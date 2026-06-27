---
title: ADR-002 Multi-Agent Architecture
status: Accepted
date: 2026-06-27
decision-makers: SentinelAI Team
---

# ADR-002: Multi-Agent Architecture

## Status

**Accepted**

---

## Context

Cybersecurity investigations require multiple forms of analysis.

Examples include:

- timeline reconstruction
- threat intelligence correlation
- graph analysis
- memory retrieval
- evidence validation
- report generation

These activities require different capabilities, reasoning strategies and data sources.

Using a single AI component for every investigation task would increase prompt complexity, reduce explainability and make future evolution difficult.

A modular approach was therefore required.

---

## Decision

SentinelAI adopts a multi-agent architecture coordinated by a Planner.

Each agent owns a single analytical responsibility.

Examples include:

- Timeline Agent
- Threat Intelligence Agent
- Graph Analysis Agent
- Memory Agent
- Validation Agent
- Report Agent

Agents never communicate directly with analysts.

Agents never coordinate one another.

Instead, every execution request is initiated by the Planner.

Validated agent outputs are synthesized by the Decision Engine into a structured investigation outcome.

The Decision Engine is part of the AI Runtime.

---

## Rationale

The selected architecture separates investigation coordination from analytical execution.

This separation enables:

- independent agent evolution
- isolated testing
- explainable reasoning
- flexible investigation workflows
- selective agent execution

Individual agents may evolve or be replaced without affecting the overall investigation workflow.

---

## Alternatives Considered

### Single LLM Workflow

A single language model performing every investigation task was considered.

Although implementation would be simpler, prompt complexity would increase significantly as new capabilities were introduced.

Reasoning steps would become difficult to explain and validate.

**Decision:** Rejected.

---

### Sequential Fixed Pipeline

A predefined sequence of investigation steps was considered.

Every investigation would execute the same analytical pipeline regardless of context.

This approach wastes computational resources and limits adaptive investigation behavior.

**Decision:** Rejected.

---

### Peer-to-Peer Agent Collaboration

Allowing agents to invoke one another directly was considered.

Although potentially flexible, this approach introduces implicit execution paths and unclear ownership.

Investigation flow becomes difficult to observe and reproduce.

**Decision:** Rejected.

---

## Consequences

### Positive

- Modular investigation architecture.
- Clear analytical responsibilities.
- Independent agent development.
- Improved explainability.
- Adaptive investigation execution.
- Simplified testing.

---

### Negative

- Additional orchestration complexity.
- Increased coordination overhead.
- More architectural components.

---

### Trade-Offs

The architecture intentionally accepts higher coordination complexity in exchange for improved modularity, explainability and long-term maintainability.

---

## Related Documents

- System Overview
- Agent Architecture
- Planner Agent
- AI Runtime
- Domain Model

---

## Notes

The Planner remains the only component responsible for coordinating investigations.

Specialized agents perform analysis only.

Future agents may be introduced without changing the coordination model established by this decision.

---

## Supersedes

None