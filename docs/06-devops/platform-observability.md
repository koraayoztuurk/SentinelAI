---
title: Platform Observability
version: 1.2.0
status: Accepted
owner: SentinelAI Team
last_updated: 2026-07-26
---

# Platform Observability

> This document defines the architectural model governing operational observability throughout SentinelAI. It establishes operational visibility, observability responsibilities and platform awareness while remaining independent of implementation technologies.

---

# 1. Purpose

Platform Observability defines how SentinelAI maintains operational visibility throughout the platform lifecycle.

Rather than prescribing telemetry technologies, monitoring platforms or operational tooling, this document establishes the architectural responsibilities governing operational visibility, platform awareness and observability consistency.

Platform Observability complements the Deployment Architecture, Environment Architecture, Configuration Management and Release Management by defining how the operational behavior of the platform is understood without modifying architectural ownership or deployment responsibilities.

Platform observability exists to improve operational understanding rather than influence architectural decision-making.

---

# 2. Design Goals

The Platform Observability architecture is designed to achieve the following goals.

## Operational Visibility

The platform should provide sufficient operational visibility to understand its runtime behavior.

Operational visibility should improve operational reasoning without introducing unnecessary complexity.

---

## Platform Awareness

Operational information should enable understanding of the current state of the platform.

Platform awareness strengthens operational confidence and supports effective platform governance.

---

## Observability Consistency

Equivalent architectural capabilities should expose equivalent operational observability characteristics.

Operational understanding should remain consistent across deployment units and operational environments.

---

## Explicit Observability Ownership

Every observable operational capability should have a clearly defined architectural owner.

Observability ownership should remain aligned with the architectural responsibilities established throughout SentinelAI.

---

## Operational Independence

Observability should support independent operation of deployment units without weakening architectural boundaries.

---

## Technology Independence

Observability principles should remain independent of telemetry technologies, monitoring platforms and operational tooling.

---

# 3. Architectural Role

Platform Observability establishes the architectural model governing operational visibility throughout SentinelAI.

Rather than defining telemetry implementations, the architecture identifies:

- operational visibility
- observability responsibilities
- platform awareness
- operational understanding
- observability consistency
- operational health visibility

Platform Observability does not define security monitoring, audit logging, accountability mechanisms or implementation-specific observability technologies.

Those responsibilities remain outside the scope of this architectural document.

The observability model should remain consistent with the Deployment Architecture, Environment Architecture, Configuration Management, Release Management and the Security Architecture while preserving architectural ownership and operational independence.

Platform Observability complements, but does not redefine, the Audit & Observability responsibilities established by the Security Architecture.

---

# 4. Observability Model

The Observability Model defines how SentinelAI provides operational understanding throughout the platform lifecycle while preserving architectural ownership and operational independence.

Observability exists to improve understanding of platform behavior rather than influence platform behavior. Observability supports operational reasoning without becoming an operational authority.

Operational visibility should enable platform operators to understand how architectural capabilities behave without modifying deployment ownership, configuration responsibilities or release progression.

The observability model is founded on the following principles:

- operational visibility
- explicit observability ownership
- operational consistency
- platform awareness
- architectural integrity

---

## Observability Boundaries

Observability boundaries define the operational scope within which platform behavior is observed and understood.

Observability should remain appropriately scoped to the deployment units, operational environments and architectural capabilities that legitimately require operational visibility.

Each observability boundary should:

- preserve architectural ownership
- reinforce deployment boundaries
- respect environment isolation
- support operational understanding
- preserve configuration consistency

Observability boundaries should never redefine architectural responsibilities.

---

## Operational Visibility

Operational visibility enables understanding of the runtime behavior of SentinelAI.

Operational visibility should provide sufficient understanding of:

- platform behavior
- deployment unit behavior
- environment behavior
- operational interactions

Operational visibility should strengthen operational reasoning without introducing unnecessary complexity.

---

## Platform Health

Platform health represents the operational condition of the platform as observed through architectural capabilities.

Platform health should reflect:

- operational availability
- operational stability
- deployment consistency
- environment consistency

Platform health should describe operational behavior rather than prescribe operational actions.

---

## Liveness and Readiness

Platform health answers two distinct operational questions, and conflating them degrades both.

**Liveness** asks whether the deployment unit is running and able to answer at all. It is independent of every dependency: a store outage is not a reason to restart a healthy process.

**Readiness** asks whether the deployment unit can serve its business responsibility *now*. It is therefore dependency-aware, and the architecture distinguishes two kinds of dependency:

- A dependency is **gating** when the deployment unit cannot fulfil its business responsibility without it. An unavailable gating dependency makes the unit not ready, and it should be removed from service rather than allowed to fail requests.
- A dependency is **degradable** when its absence reduces capability without preventing the unit's business responsibility. A degradable dependency is **probed and reported truthfully** but does not gate readiness: gating on it would convert a partial capability loss into a total outage.

Whether a dependency gates follows from **who owns the data it holds**. A store holding data the platform is authoritative for is gating; a store holding a derived representation, whose absence the owning capability already degrades around, is not.

Readiness reporting should remain **truthful about every dependency regardless of whether it gates** — an operator must be able to see a degraded dependency without the platform having to fail in order to disclose it.

---

## Observability Consistency

Equivalent architectural capabilities should expose equivalent operational observability characteristics.

Operational understanding should remain consistent across deployment units and operational environments.

Maintaining observability consistency simplifies governance, operational reasoning and long-term platform evolution.

---

# 5. Observability Domains

Platform Observability recognizes multiple logical areas of operational understanding.

Observability domains describe operational responsibilities rather than architectural ownership boundaries.

---

## Platform Operational Visibility

Platform Operational Visibility provides operational understanding of SentinelAI as a complete operational system.

Its responsibilities include:

- understanding platform behavior
- supporting operational awareness
- maintaining platform visibility
- preserving operational consistency

Platform Operational Visibility should remain independent of deployment technologies.

---

## Deployment Observability

Deployment Observability provides operational understanding of deployment units.

Its responsibilities include:

- understanding deployment behavior
- observing deployment health
- supporting deployment visibility
- preserving deployment independence

Deployment Observability should remain aligned with deployment ownership.

---

## Environment Observability

Environment Observability provides operational understanding of individual operational environments.

Its responsibilities include:

- understanding environment behavior
- supporting environment awareness
- preserving operational isolation
- maintaining environment consistency

Environment Observability should never redefine environment responsibilities.

---

## Domain Observability

Each architectural domain contributes operational visibility appropriate to its own operational responsibilities.

Domain Observability should:

- remain aligned with architectural ownership
- preserve deployment boundaries
- avoid unnecessary operational coupling
- remain compatible with platform-wide observability principles

---

## Relationship Between Observability Domains

Observability domains differ according to operational scope rather than architectural authority.

Every observability domain contributes to platform understanding while preserving architectural ownership, deployment independence and operational consistency.

Observability domains should cooperate through clearly defined operational responsibilities without creating overlapping ownership.

Observability domains differ in operational perspective rather than architectural responsibility.

---

# 6. Observability Responsibilities

Observability responsibilities define the architectural ownership of operational visibility throughout SentinelAI.

Rather than assigning ownership to telemetry platforms, monitoring technologies or operational tooling, the architecture assigns responsibility according to the architectural domains and deployment units whose operational behavior is observed.

Every observable operational capability should have a clearly identified owner responsible for preserving operational understanding, observability consistency and architectural alignment.

Observability ownership should remain independent of the technologies used to observe operational behavior.

Observability responsibilities should remain explicit and should never become implicitly shared across unrelated architectural domains.

---

## Platform Operational Visibility Responsibilities

Platform Operational Visibility is responsible for:

- maintaining platform-wide operational visibility
- supporting platform awareness
- preserving operational consistency
- strengthening operational understanding

Platform Observability should evolve according to the operational needs of the platform.

---

## Deployment Observability Responsibilities

Deployment Observability is responsible for:

- understanding deployment behavior
- preserving deployment visibility
- supporting deployment health awareness
- maintaining deployment consistency

Deployment Observability should remain aligned with deployment ownership.

---

## Environment Observability Responsibilities

Environment Observability is responsible for:

- understanding environment behavior
- maintaining environment visibility
- preserving operational isolation
- supporting environment awareness

Environment Observability should always respect the operational purpose of each environment.

---

## Domain Observability Responsibilities

Each architectural domain is responsible for exposing the operational visibility necessary to understand its own operational behavior.

Domain responsibilities include:

- maintaining operational transparency
- preserving architectural ownership
- minimizing unnecessary observability dependencies
- remaining compatible with platform-wide observability principles

Observability ownership should always remain within the architectural domain responsible for the observed capability.

---

## Cross-Domain Responsibilities

All architectural domains contribute to a consistent observability model.

Shared responsibilities include:

- preserving observability boundaries
- maintaining observability consistency
- respecting observability ownership
- minimizing unnecessary operational coupling
- supporting platform awareness

Cross-domain collaboration should strengthen operational understanding without weakening architectural ownership.

---

# 7. Observability Principles

The architecture establishes the following principles for governing operational observability throughout SentinelAI.

These principles remain independent of telemetry technologies, monitoring platforms and operational tooling.

---

## Explicit Observability Ownership

Every observable operational capability should have a clearly identified architectural owner.

Observability ownership should remain stable throughout the operational lifecycle and should never become ambiguous as the platform evolves.

---

## Operational Visibility

Operational visibility should provide sufficient understanding of platform behavior without introducing unnecessary operational complexity.

Operational visibility should remain aligned with:

- deployment ownership
- environment responsibilities
- configuration responsibilities
- release responsibilities
- observability boundaries

Operational visibility should strengthen operational reasoning rather than operational intervention.

---

## Observability Isolation

Operational visibility should remain appropriately scoped.

Observability for one deployment unit or environment should not unnecessarily weaken the operational independence of unrelated architectural capabilities.

Observability isolation strengthens deployment independence and operational governance.

---

## Platform Awareness

Operational understanding should enable informed awareness of platform behavior throughout the operational lifecycle.

Platform awareness should improve operational reasoning while preserving architectural consistency and deployment independence.

---

## Observability Consistency

Equivalent architectural capabilities should expose equivalent operational observability characteristics.

Observability consistency simplifies governance, operational reasoning and long-term platform evolution.

---

## Architectural Integrity

Platform observability should support architectural understanding without redefining architectural responsibilities.

Operational visibility may improve understanding of platform behavior but should never modify deployment ownership, configuration responsibilities, release progression or architectural authority.

Maintaining architectural integrity ensures that observability remains a supporting capability rather than an architectural authority.

---

# 8. Operational Awareness

Platform Observability supports operational awareness throughout the SentinelAI platform lifecycle by enabling architectural understanding of runtime behavior without influencing architectural responsibilities.

Operational Awareness defines how platform understanding is maintained throughout the operation of SentinelAI without prescribing implementation-specific monitoring workflows or operational procedures.

Operational awareness should remain understandable, consistent and aligned with the architectural model established throughout the platform.

The architecture establishes the following awareness principles.

---

## Awareness Establishment

Operational awareness should begin with a clearly defined understanding of the architectural capabilities being observed.

Awareness establishment should identify:

- observable operational capabilities
- operational objectives
- architectural ownership
- operational scope

Operational awareness should never exist without an identified architectural responsibility.

---

## Awareness Evolution

Operational awareness should evolve together with the operational maturity of the platform.

Awareness evolution should:

- preserve architectural integrity
- maintain operational consistency
- respect observability boundaries
- strengthen operational understanding

Operational awareness should evolve deliberately rather than incidentally.

---

## Operational Understanding

Operational awareness should provide sufficient understanding to explain platform behavior throughout its operational lifecycle.

Operational understanding should:

- preserve deployment ownership
- remain compatible with environment responsibilities
- support configuration understanding
- remain consistent with release progression
- preserve observability ownership

Operational understanding should improve confidence without influencing architectural responsibilities.

---

## Awareness Continuity

Operational awareness should remain continuous throughout platform operation.

Continuity should:

- preserve platform understanding
- maintain operational consistency
- support architectural reasoning
- strengthen operational governance

Operational continuity should remain independent of implementation technologies or operational tooling.

---

## Awareness Traceability

Operational awareness should remain understandable throughout platform evolution.

Operational understanding should remain attributable to architectural responsibilities while preserving observability ownership and architectural integrity.

Awareness traceability complements operational governance without redefining the accountability responsibilities established by the Security Architecture. Operational traceability complements, but does not replace, the architectural accountability established by Audit & Observability.

---

# 9. Extensibility

The Platform Observability architecture is designed to evolve together with SentinelAI while preserving its architectural observability model.

Future architectural capabilities should integrate into the existing observability model without altering observability ownership, operational visibility or architectural integrity.

New observability capabilities should:

- define explicit observability ownership
- preserve observability boundaries
- maintain operational consistency
- strengthen operational awareness
- remain compatible with deployment, environment, configuration and release responsibilities
- reinforce architectural governance

Architectural evolution should simplify operational understanding rather than increase operational complexity.

---

# 10. Future Evolution

Future versions of the Platform Observability architecture may introduce:

- organization-specific operational visibility models
- adaptive observability strategies
- advanced operational awareness capabilities
- observability dependency analysis
- automated operational insight generation
- platform-wide observability standardization
- operational visibility optimization strategies

Future enhancements should preserve the architectural principles established by this document.

Regardless of future platform evolution, explicit observability ownership, operational visibility and architectural integrity should remain fundamental characteristics of Platform Observability.

---

# 11. Design Principles Applied

The Platform Observability architecture follows the engineering principles established throughout SentinelAI.

| Principle | Platform Observability Application |
|-----------|------------------------------------|
| Human-Centered AI | Operational visibility supports reliable platform operation while improving understanding for analysts and platform operators. |
| Explainability | Operational visibility, observability ownership and platform awareness remain explicit and understandable. |
| Separation of Responsibilities | Platform Observability improves operational understanding without assuming deployment, configuration, release or security responsibilities. |
| Modularity | Operational visibility remains appropriately scoped to architectural domains, deployment units and operational environments. |
| Least Privilege | Observability remains limited to the operational capabilities legitimately requiring visibility. |
| Defense in Depth | Operational visibility complements deployment, environment and security boundaries by strengthening operational understanding. |
| Architecture Before Framework | Observability principles remain independent of telemetry technologies, monitoring platforms and operational tooling. |

---

# Closing Statement

Platform Observability establishes the architectural foundation for understanding the operational behavior of SentinelAI throughout its platform lifecycle.

By defining observability ownership, operational visibility, platform awareness and awareness principles, the architecture enables reliable operational understanding while preserving deployment independence, environment isolation, configuration consistency and release integrity.

This document complements the Deployment Architecture, Environment Architecture, Configuration Management, Release Management and the Security Architecture by defining how operational behavior is understood without redefining architectural responsibilities.

Future observability capabilities should extend these architectural principles while preserving explicit ownership, operational consistency and the Architecture First philosophy established throughout SentinelAI.

Platform Observability should continue to evolve together with the platform while preserving architectural integrity, operational visibility and explicit observability ownership.

---

# Known Gaps (Release 1.0)

Recorded per ADR-020 §3: each item below is deliberately open. It states what the platform does today in its place and the governance path that would close it (documentation, ADR, or RFC per the ADR-014 threshold).

- **Metrics are exposed, not collected.** The platform serves its own counters and gauges; no scraper, time-series store, dashboard or alerting exists, and there are no histograms or per-endpoint labels (a deliberate cardinality bound).
- **Logs are written to standard output only.** Shipping, aggregation, retention and a structured-log schema contract are unspecified.
- **Tracing is correlation-id threading**, not distributed tracing: there are no spans and no cross-process trace propagation.
- **Client-side observability is an error boundary.** Frontend errors are contained and rendered; nothing is reported back to the platform.
- **All counters are per instance**, consistent with the single-instance deployment posture (deployment-architecture.md).

---

# Version History

| Version | Date | Description |
|----------|------------|--------------------------------|
| 1.0.0 | 2026-06-28 | Initial Platform Observability specification created |
| 1.1.0 | 2026-07-26 | Liveness/readiness distinction specified (§4): liveness is dependency-independent, readiness is dependency-aware, and a dependency **gates** readiness when the unit cannot fulfil its business responsibility without it while a **degradable** dependency is reported truthfully but never gates — gating on one would turn a partial capability loss into a total outage. Whether a dependency gates follows from data ownership: authoritative stores gate, derived representations do not. Resolves the documented readiness deviation; realized by ES-069 |
| 1.2.0 | 2026-07-26 | Status Draft → **Accepted** (ADR-020 §2) with a Known Gaps section (§3): the absent collection stack, log shipping, distributed tracing, client observability and the per-instance scope of every counter stated as open |
