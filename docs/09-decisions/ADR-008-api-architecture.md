---
title: ADR-008 API Architecture
status: Accepted
date: 2026-06-27
decision-makers: SentinelAI Team
---

# ADR-008: API Architecture

## Status

**Accepted**

---

## Context

SentinelAI consists of multiple frontend modules, backend services and AI capabilities.

A consistent communication model is required to prevent frontend components from becoming tightly coupled to backend implementation details.

The platform also requires a stable integration layer that can evolve independently from internal services.

---

## Decision

SentinelAI adopts a Backend API as the single entry point for all client communication.

The Backend API is responsible for:

- request routing
- authentication
- authorization
- request validation
- response formatting
- error translation

Business logic remains implemented within backend services.

The API acts as a communication boundary rather than a business execution layer.

---

## Rationale

Using a single API boundary provides:

- consistent communication
- stable client interfaces
- independent backend evolution
- centralized security
- simplified frontend development

The architecture prevents client applications from depending on internal service organization.

---

## Alternatives Considered

### Direct Frontend-to-Service Communication

Allowing the frontend to communicate directly with backend services was considered.

This tightly couples frontend implementation to backend service organization and complicates future architectural changes.

**Decision:** Rejected.

---

### Business Logic in Controllers

Implementing business logic directly within API controllers was considered.

This reduces maintainability, duplicates responsibilities and complicates testing.

**Decision:** Rejected.

---

### Backend-for-Frontend (BFF)

A dedicated Backend-for-Frontend layer was considered.

While beneficial for multiple client types, it introduces unnecessary complexity for the current architecture.

This option may be reconsidered as SentinelAI evolves.

**Decision:** Rejected.

---

## Consequences

### Positive

- Stable frontend integration.
- Centralized security enforcement.
- Improved maintainability.
- Clear responsibility boundaries.
- Independent service evolution.

---

### Negative

- Additional communication layer.
- Increased request routing responsibility.
- Slightly higher implementation complexity.

---

### Trade-Offs

The architecture introduces an additional abstraction layer to preserve loose coupling and long-term maintainability.

---

## Related Documents

- API Design
- Frontend Architecture
- Backend Architecture
- Investigation Service
- Memory Service
- Graph Service

---

## Notes

The Backend API owns communication responsibilities only.

Business ownership remains within backend services.

Future API technologies may change without affecting architectural responsibilities.

---

## Supersedes

None
