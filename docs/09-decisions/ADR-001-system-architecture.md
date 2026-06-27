---
title: ADR-001 System Architecture
status: Accepted
date: 2026-06-27
decision-makers: SentinelAI Team
---

# ADR-001: Overall System Architecture

## Status

**Accepted**

---

## Context

SentinelAI is designed as an AI-assisted cybersecurity investigation platform.

The platform must support long-running investigations involving multiple AI components, structured knowledge, graph reasoning and analyst interaction.

Several architectural styles were considered during the initial system design.

The selected architecture needed to satisfy the following requirements:

- clear separation of responsibilities
- explainable AI reasoning
- long-term maintainability
- independent subsystem evolution
- support for future AI capabilities
- technology independence

The architecture also needed to prevent tight coupling between user interfaces, AI components and persistence technologies.

---

## Decision

SentinelAI adopts a layered architecture composed of independent architectural domains.

The primary architectural layers are:

- Presentation
- Backend Services
- AI Runtime
- Knowledge Layer
- Infrastructure

Each layer owns clearly defined responsibilities.

Communication occurs only through explicit architectural boundaries.

No layer may bypass another layer to access internal implementation details.

Business logic remains within backend services.

AI reasoning remains within the AI Runtime.

Persistence remains isolated behind dedicated backend services.

Presentation remains responsible only for user interaction.

---

## Alternatives Considered

### Monolithic Architecture

A traditional monolithic architecture was considered.

This approach would simplify initial implementation.

However, it would tightly couple business logic, AI reasoning and persistence.

As the platform evolves, maintainability and scalability would become increasingly difficult.

**Decision:** Rejected.

---

### AI-Centric Architecture

Another alternative placed the language model at the center of the platform.

Backend services would become thin wrappers around AI execution.

Although this approach reduces application logic, it creates excessive dependence on language models.

Business rules become difficult to validate and explain.

**Decision:** Rejected.

---

### Microservices Architecture

A fully distributed microservice architecture was also considered.

While highly scalable, it introduces operational complexity that is unnecessary for the current stage of SentinelAI.

The platform does not yet require independent deployment of every subsystem.

**Decision:** Rejected.

---

## Consequences

### Positive

- Strong separation of responsibilities.
- Clear architectural ownership.
- Technology-independent design.
- Easier testing and maintenance.
- Independent evolution of architectural layers.
- Improved explainability.

---

### Negative

- More architectural documents must be maintained.
- Additional abstraction increases initial implementation effort.
- Layer boundaries require discipline during development.

---

### Trade-Offs

The selected architecture intentionally favors long-term maintainability over short-term implementation simplicity.

This increases initial design effort but significantly improves future extensibility and architectural consistency.

---

## Related Documents

- System Overview
- Frontend Architecture
- Backend Architecture
- AI Runtime
- API Design
- Database Architecture
- Domain Model

---

## Notes

This decision establishes the highest-level architectural structure of SentinelAI.

Future architectural decisions must remain compatible with the layered architecture defined in this ADR unless this decision is explicitly superseded.

---

## Supersedes

None