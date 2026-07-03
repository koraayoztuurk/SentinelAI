---
title: ADR-013 AI Provider Resilience and the Single Agent Execution Path
status: Accepted
date: 2026-07-03
decision-makers: SentinelAI Team
---

# ADR-013: AI Provider Resilience and the Single Agent Execution Path

## Status

**Accepted**

---

## Context

Two related gaps were identified by the architecture gap analysis (`ARCHITECTURE-GAPS-2026-07-03.md`, E-02 and D-03):

1. **No provider resilience policy existed.** The provider ports (`LLMProvider`, `EmbeddingProvider`) defined no time-bound behavior, and a provider failure inside the Planner Agent's reasoning propagated out of the Investigation Loop as an exception — no retry, degrade or containment behavior was decided anywhere.

2. **Two agent execution paths existed.** The Agent Runtime hosted a string-payload envelope with failure containment, while the concrete agents ran through typed methods (`decide`, `plan`) that **bypassed** the runtime — so the runtime's only guarantee (no exception escapes) was inactive exactly where it mattered. With four or more specialized agents planned, maintaining two contracts is unsustainable.

---

## Decision

### 1. Provider calls are time-bounded at the port contract

Every provider port implementation must enforce a bounded execution time. Exceeding the bound is surfaced as the port's failure type (for example `LLMProviderError`) — never as an indefinite hang. Timeout values are configuration, not architecture; the **existence** of the bound is the contract.

### 2. One agent execution path: the typed Agent Runtime

- The agent contract is **generic and typed**: an agent exposes `execute(request) → product`, where request and product are the agent's own typed structures (realizing Agent Architecture §15: the product is *represented through* the neutral envelope without coupling the envelope to any product type).
- The **Agent Runtime** is the only execution host: it runs the agent, contains every failure (domain errors as stable codes, unexpected errors as a fixed code) and returns a typed result envelope. No exception escapes the runtime.
- Agents raise on failure; they do not build failure envelopes themselves. The envelope belongs to the runtime.
- Compositions (Investigation Loop, Retrieval Flow) invoke agents **only** through the runtime.

### 3. Degrade-to-escalation is the loop's failure mode

When an agent execution fails inside the Investigation Loop — provider outage, timeout, precondition violation — the loop does not crash and does not retry blindly: it ends the run as **ESCALATED**, carrying the stable failure code, and the investigation remains intact for the human analyst. AI unavailability degrades the platform to human-driven investigation; it never corrupts investigation state. (This is the resilience realization of the Human-Centered AI principle.)

Retry-worthy transient failures are the Planner Agent's replanning concern across cycles (planner-agent §12) — observed through failed execution results — not hidden infrastructure retries inside the loop.

### 4. Circuit breaking is a concrete-provider concern

A circuit-breaker (fail-fast on an unhealthy provider) is the designated pattern for concrete provider adapters, applied at the infrastructure/provider edge when real providers are integrated. It is not implemented in the provider-neutral ports.

---

## Rationale

- A single typed execution path restores the runtime's containment guarantee on the real execution route and gives every future agent one contract to satisfy — the cost of unification is two agents today versus six-plus later.
- Escalation-as-degrade matches the documented investigation model: escalation is already a *successful* outcome when reliable conclusions cannot be reached (planner-agent §10); provider failure is exactly such a case.
- Keeping timeout values and breaker thresholds out of the architecture preserves technology independence while making the *existence* of bounds non-negotiable.
- Verifiability: "no exception escapes an agent run" and "loop ends ESCALATED with a stable code on decision failure" are directly testable properties (and are tested).

---

## Alternatives Considered

### Infrastructure-level automatic retries inside the loop

Retrying failed provider calls transparently within a cycle.

Hidden retries make investigation duration unpredictable, mask provider health, and duplicate the Planner Agent's documented replanning responsibility.

**Decision:** Rejected.

---

### Keeping both execution paths (string envelope + typed bypass)

Leaving the runtime as an optional host.

The runtime's guarantee then holds only where it is least needed; every new agent doubles the divergence.

**Decision:** Rejected.

---

### Failing the investigation on provider failure

Treating provider unavailability as a fatal investigation error.

This inverts the platform's human-centered premise: the analyst can always continue without AI; the AI must never take the investigation down with it.

**Decision:** Rejected.

---

## Consequences

### Positive

- Provider failures have one defined, observable, tested behavior end to end.
- One agent contract for all future agents; containment is structural, not conventional.
- The analyst experience degrades gracefully instead of erroring.

### Negative

- The typed generic contract is slightly more abstract than the previous string envelope.
- Escalated-by-failure runs require analyst attention (by design).

### Trade-Offs

A small amount of generic-typing complexity is accepted in exchange for a single, guaranteed-contained execution path.

---

## Related Documents

- Agent Architecture (§6a AI Runtime, §15 Agent Contract)
- Planner Agent (§12 Failure Recovery)
- ADR-005 AI Runtime, ADR-010 Planner Composition

---

## Notes

This ADR resolves audit findings **E-02** and **D-03**. Concrete provider adapters (with real timeouts and circuit breakers) remain deferred integration work (implementation tracker).

---

## Supersedes

None
