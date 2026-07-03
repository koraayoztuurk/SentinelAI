---
title: ADR-010 Planner Composition and AI Orchestration Ownership
status: Accepted
date: 2026-07-03
decision-makers: SentinelAI Team
---

# ADR-010: Planner Composition and AI Orchestration Ownership

## Status

**Accepted**

---

## Context

ADR-002 established the Planner as the single coordinator of investigations, and ADR-005 placed the Planner inside the AI Runtime. The backend architecture documents (Planner Service, API Design, Database Architecture) subsequently introduced a **Planner Service** in the Application Domain — a component that executes backend operations on behalf of the Planner.

This produced three unresolved architectural questions:

1. **The split itself was never decided.** ADR-004 permits new backend services only when they own a distinct business capability, and requires a superseding decision before responsibilities are redistributed. The Planner Service owns no business data and no business capability, so its existence as a backend component was architecturally unjustified at the ADR level.

2. **Composition ownership was undefined.** The Planner Agent selects exactly one Planner Action per cycle, and the Planner Service executes exactly one Planner Action per request — but no architectural component owned the loop that connects them, and no document said which layer may own it. The same gap existed between the Memory Agent (which selects retrieval strategies) and the RAG Pipeline (which executes them).

3. **The dependency direction was ambiguous.** ADR-005 states that "backend services request AI capabilities through well-defined interfaces", implying the backend calls the AI Runtime. The implementation direction is the reverse: the AI Runtime consumes backend service interfaces, and nothing in the backend depends on AI components.

---

## Decision

### 1. The Planner is realized as two components

- The **Planner Agent** (AI Runtime) owns planning: it reasons over an already-assembled Investigation State and emits exactly one Planner Action per cycle.
- The **Planner Service** (Application Domain) owns execution: it validates and executes exactly one Planner Action per request against the owning backend service, returning a provenance-bearing execution result.

The Planner Service is an **orchestration seam**, not a business-capability service. This ADR amends ADR-004 by introducing this category explicitly: an orchestration seam owns no business data, persists no state, and exists solely to give the AI Runtime a single, validated execution boundary over the backend services. ADR-004's ownership rules for business capabilities remain unchanged.

### 2. The AI Runtime owns composition

The compositions that connect agents to executors belong to the **AI Runtime** (ADR-005: planning, reasoning and decision synthesis are AI Runtime responsibilities):

- The **Investigation Loop** owns the Planner decision loop: Planner Agent decides → Planner Service executes → the next Investigation State is observed → the cycle repeats until the agent issues a control action (complete / escalate) or a caller-supplied cycle budget is exhausted.
- The **Retrieval Flow** owns the memory composition: Memory Agent selects retrieval strategies → RAG Pipeline executes them into a validated Investigation Context and its prompt.

Investigation State assembly remains **outside** the loop, behind a replaceable port. Concrete assembly belongs to the Investigation Workspace / Context Builder responsibility defined by the Planner Agent and RAG architecture documents; the loop only consumes it.

### 3. The dependency direction is one-way: AI Runtime → Application

The AI Runtime depends on backend service interfaces (to obtain knowledge and to execute actions). Backend services never depend on the AI Runtime. This resolves the ambiguity in ADR-005's wording: backend components do not invoke AI components; the AI Runtime composes backend capabilities.

This direction is an enforceable architectural constraint (see Architecture Testing, Architectural Constraint Catalogue).

### 4. The single-action control model is normative

The Planner Service executes one Planner Action per request and persists no workflow state. Multi-step, adaptive investigation is realized exclusively by the Planner Agent's iterative decision loop, hosted by the Investigation Loop. Stateful, multi-step workflow orchestration inside the Planner Service is rejected.

---

## Rationale

- Planning quality and execution reliability evolve independently when decision-making (AI) and execution (backend) are separate components with a typed contract between them.
- A single, AI Runtime-owned composition point keeps ADR-002's coordination model intact: agents still never call one another; every execution request still originates from the Planner.
- A one-way dependency direction keeps backend services free of AI concerns, preserves their independent testability, and makes the boundary statically verifiable.
- A stateless, single-action execution seam avoids a second source of truth for investigation progress: investigation state remains owned by the Investigation Service; the loop holds no state of its own.

---

## Alternatives Considered

### Backend-owned orchestration (backend calls the AI Runtime)

The Application Domain would own the loop and invoke the Planner Agent as a capability.

This matches a literal reading of ADR-005's wording, but couples backend services to AI components, reverses the knowledge-access direction ADR-005 also mandates ("AI components obtain organizational knowledge exclusively through backend service interfaces"), and makes the backend untestable without AI doubles.

**Decision:** Rejected.

---

### Stateful workflow orchestrator in the Planner Service

The Planner Service would receive and persist multi-step execution plans, coordinating ordering, dependencies and recovery.

This duplicates investigation progress in a second store, contradicts adaptive planning (plans change after every observation), and turns an orchestration seam into a de facto business service.

**Decision:** Rejected.

---

### No dedicated composition component

Callers (for example API controllers) would wire agent and executor per use case.

This scatters the loop across the presentation layer, makes cycle budgeting and termination policy inconsistent, and puts AI orchestration in a layer that must not own it.

**Decision:** Rejected.

---

## Consequences

### Positive

- The Planner split is now an explicit, governed decision rather than an implementation artifact.
- The composition point has a single owner and a typed, testable contract.
- The dependency direction is decided and statically enforceable.
- ADR-004's business-ownership model remains intact and is clarified rather than weakened.

### Negative

- One additional AI Runtime component (the composition layer) must be maintained.
- The Investigation State assembly port adds an abstraction whose concrete implementation is still deferred.

### Trade-Offs

The architecture accepts one more explicit component in exchange for removing an undefined responsibility — the most likely erosion point of the multi-agent model.

---

## Related Documents

- Agent Architecture
- Planner Agent
- Planner Service
- RAG Architecture
- API Design
- Architecture Testing

---

## Notes

This ADR **amends** (does not supersede):

- **ADR-002** — clarifies that "the Planner" is realized as the Planner Agent plus the Planner Service, composed by the AI Runtime; the coordination model is unchanged.
- **ADR-004** — introduces the orchestration-seam category and thereby provides the superseding decision ADR-004 requires for the Planner Service's existence.
- **ADR-005** — fixes composition ownership (AI Runtime) and the dependency direction (AI Runtime → Application, one-way).

The exposure of Planner Action execution through the public API is a separate, still-open decision (it is transitional until the Investigation Loop has a runtime invocation surface) and is intentionally not decided here.

---

## Supersedes

None
