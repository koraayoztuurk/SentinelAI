---
title: ADR-005 AI Runtime
status: Accepted
date: 2026-06-27
decision-makers: SentinelAI Team
---

# ADR-005: AI Runtime Architecture

## Status

**Accepted**

---

## Context

SentinelAI relies on artificial intelligence to perform specialized investigation tasks.

These tasks include planning, graph reasoning, memory retrieval, evidence validation and report generation.

Embedding AI capabilities directly into backend services would tightly couple business logic with model execution.

The platform therefore requires a dedicated architectural layer responsible for AI orchestration and execution.

---

## Decision

SentinelAI adopts a dedicated AI Runtime as an independent architectural layer.

The AI Runtime is responsible for executing AI workloads while remaining separate from backend business services.

The AI Runtime includes:

- Planner
- Specialized Agents
- Decision Engine
- RAG Pipeline
- Provider Interfaces

Backend services request AI capabilities through well-defined interfaces.

Backend services never implement AI reasoning directly.

The AI Runtime never communicates directly with persistence technologies.

---

## Responsibilities

The AI Runtime is responsible for:

- agent execution
- planning
- reasoning
- retrieval-augmented generation
- decision synthesis
- model provider abstraction

The AI Runtime is not responsible for:

- business ownership
- database access
- user interaction
- investigation persistence
- authentication

These responsibilities remain outside the AI Runtime.

---

## Rationale

Separating AI execution from backend services provides:

- independent AI evolution
- provider independence
- simplified experimentation
- improved maintainability
- clearer architectural ownership

The architecture allows AI components to evolve without changing business services.

---

## Alternatives Considered

### AI Embedded in Backend Services

Backend services directly invoking language models was considered.

This approach couples business logic to AI implementation and complicates testing and maintenance.

**Decision:** Rejected.

---

### Single AI Service

A single component responsible for every AI capability was considered.

As SentinelAI evolves, this approach would become difficult to maintain and extend.

**Decision:** Rejected.

---

### External AI Platform

Delegating all AI execution to an external orchestration platform was considered.

While operationally attractive, it would reduce architectural control and increase dependence on third-party infrastructure.

**Decision:** Rejected.

---

## Consequences

### Positive

- Clear separation between business logic and AI reasoning.
- Independent evolution of AI components.
- Easier provider replacement.
- Improved maintainability.
- Better testing capabilities.

---

### Negative

- Additional architectural layer.
- Increased orchestration complexity.
- More component interfaces.

---

### Trade-Offs

The architecture intentionally introduces an additional execution layer in exchange for long-term flexibility, modularity and provider independence.

---

## Related Documents

- System Overview
- Agent Architecture
- Planner Agent
- RAG Architecture
- Backend Architecture

---

## Notes

The AI Runtime owns AI execution only.

Business ownership remains within backend services.

Future AI technologies may replace current implementations provided they preserve the architectural responsibilities established by this decision.

AI components obtain organizational knowledge exclusively through backend service interfaces.

The AI Runtime never accesses persistence technologies directly.

---

## Supersedes

None