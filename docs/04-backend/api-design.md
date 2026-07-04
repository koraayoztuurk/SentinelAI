---
title: SentinelAI API Design
version: 1.3.0
status: Draft
owner: SentinelAI Team
last_updated: 2026-07-04
---

# SentinelAI API Design

> This document defines the external API architecture of SentinelAI. The API provides a secure and technology-independent interface between client applications and backend services.

---

# 1. Purpose

The SentinelAI API exposes backend capabilities to external clients.

Rather than embedding business logic within HTTP endpoints, the API delegates all business operations to dedicated backend services.

The API serves as the external communication layer of the platform.

Its primary objective is providing secure, consistent and maintainable access to backend functionality.

---

# 2. Responsibilities

The API is responsible for:

- receiving client requests
- validating requests
- authenticating clients
- invoking backend services
- formatting responses
- exposing API documentation

The API exposes backend capabilities.

It does not implement business logic.

---

# 3. High-Level Architecture

```mermaid
flowchart TD

Client --> API

API --> InvestigationService

API --> MemoryService

API --> GraphService

API --> PlannerService
```

---

# 4. API Boundaries

The API intentionally limits its responsibilities.

Business rules remain within backend services.

---

## The API Is Responsible For

- request validation
- authentication
- authorization
- response formatting
- error translation

---

## The API Is Not Responsible For

- workflow orchestration
- investigation management
- graph processing
- memory management
- AI reasoning

These responsibilities belong to backend services.

---

# 5. API Philosophy

The SentinelAI API follows a thin-controller architecture.

HTTP endpoints should remain lightweight.

Business decisions should always be delegated to backend services.

The API represents an application boundary rather than an implementation boundary.

Clients interact with stable business capabilities rather than backend implementation details.

---

## API Versioning

The SentinelAI API should expose explicit version identifiers.

Versioning enables backward compatibility while allowing the API to evolve over time.

Breaking changes should result in a new API version.

Non-breaking improvements should preserve existing API contracts.

---

## Design Principles

The API should be:

- predictable
- stateless
- versioned
- observable
- technology-independent

---

## Separation of Responsibilities

Controllers should:

- validate requests
- invoke backend services
- return standardized responses

Controllers should never directly access databases.

Controllers should never access repositories directly.

All persistence operations must be delegated to backend services.

Repository abstractions remain an internal implementation detail of the backend and are never exposed through the API layer.

---

# 6. Request Lifecycle

Every API request follows a consistent processing pipeline.

The API should remain responsible for communication concerns while delegating business operations to backend services.

```mermaid
flowchart TD

Client

--> RequestValidation

--> Authentication

--> Authorization

--> BackendService

--> ResponseFormatting

--> Logging

--> Client
```

---

**Routing Rule**

`BackendService` represents the backend service responsible for the requested operation.

- Investigation, Evidence, Finding and Report operations are delegated to the **Investigation Service**.
- Memory operations are delegated to the **Memory Service**.
- Graph operations are delegated to the **Graph Service**.
- Planner Action execution is delegated to the **Planner Service** — one action per request (ADR-010). Multi-step investigations are sequenced by the Planner Agent's decision loop in the AI Runtime, never by the API or the Planner Service.

This routing model preserves service ownership boundaries while keeping the Planner Service a stateless, single-action execution seam.

---

# 7. Service Delegation

The API delegates business operations to backend services.

Business logic should never execute inside controllers.

Service delegation should remain independent of persistence implementation details.

Whether a backend service uses relational databases, graph databases, vector databases or caching technologies should remain completely transparent to API clients.

---

## Planner Service

The API delegates the execution of a single Planner Action to the Planner Service (ADR-010).

---

## Investigation Service

The API delegates investigation lifecycle operations to the Investigation Service.

---

## Memory Service

The API delegates memory operations to the Memory Service.

---

## Graph Service

The API delegates graph operations to the Graph Service.

Delegation should preserve service ownership boundaries.

---

# 8. API Resources

The API exposes resources representing SentinelAI business objects.

Resources should remain stable regardless of backend implementation.

---

## Investigation Resource

Represents investigation lifecycle management.

---

## Evidence Resource

Represents investigation evidence.

---

## Finding Resource

Represents investigation findings.

---

## Memory Resource

Represents organizational knowledge.

---

## Graph Resource

Represents graph-based investigation data.

---

## Investigation Run Resource

Represents one synchronous execution of the Investigation Loop for an investigation (`POST /api/v1/investigations/{id}/run`).

The run surface is the investigation-level invocation surface ADR-010 anticipated: the AI Runtime's Planner decision loop decides and executes one action per cycle within a small, configurable cycle budget, records every decision, execution and outcome into the Investigation Trace, and returns a run summary (terminal condition — completed / escalated / exhausted —, cycle count, per-action results and the stable failure code when the run escalated on a provider failure, ADR-013).

A provider failure is never an HTTP error: the run responds successfully with an `escalated` outcome and the investigation remains intact.

The formerly documented transitional Planner Action Resource (`POST /api/v1/planner/actions`) was removed when this surface arrived (its stated supersession); the Planner Service remains the application-layer execution boundary behind the loop and is not directly exposed. External clients driving raw Planner Actions would invert ADR-002's coordination model and remain unsupported.

---

## Resource Ownership

Each API resource should map to exactly one backend service.

The API should never combine ownership across multiple services.

Cross-service coordination is the responsibility of the Planner Agent's decision loop, executed one action at a time through the Planner Service (ADR-010).

---

# 9. Response Model

Every API response should follow a consistent structure.

Responses should remain predictable regardless of endpoint.

---

## Successful Responses

Successful responses should include:

- requested resource
- response metadata
- execution status
- request identifier
- correlation identifier

Correlation identifiers enable distributed tracing across backend services.

They improve observability and debugging.

---

## Error Responses

Error responses should include:

- error code
- error message
- request identifier

Internal implementation details should never be exposed.

---

## Metadata

Response metadata may include:

- timestamp
- API version
- processing duration

Metadata improves observability and debugging.

---

# 10. Request Validation

Every incoming request should be validated before backend execution.

Validation failures should prevent unnecessary service invocation.

---

## Structural Validation

Validation includes:

- required fields
- supported request schema
- data types

---

## Business Validation

Business validation remains the responsibility of backend services.

The API validates structure rather than business rules.

---

## Security Validation

Validation includes:

- authentication status
- authorization rules
- request integrity

Invalid requests should return standardized error responses.

---

## Traffic Validation

Traffic validation may include:

- rate limiting
- request throttling
- abuse detection

Traffic protection preserves backend availability.

---

# 11. Error Handling

The API should expose consistent and predictable error behavior.

Errors should help clients understand failures without revealing internal implementation details.

---

## Client Errors

Examples include:

- invalid request
- malformed payload
- unsupported operation
- unauthorized access

Client errors should return standardized error responses.

---

## Backend Errors

Backend service failures should be translated into API-level responses.

Internal service details should never be exposed.

Backend service errors should be translated into consistent API error models.

Different backend services should never expose different error formats.

Backend persistence technologies should never influence externally visible API contracts.

Storage-specific exceptions should always be translated into standardized API error responses.

---

## Unexpected Errors

Unexpected failures should:

- generate diagnostic logs
- return generic error responses
- preserve request identifiers

Unexpected failures should remain observable for debugging.

---

# 12. Authentication and Authorization

The API validates client identity before backend execution.

Authorization determines whether authenticated clients may perform specific operations.

---

## Authentication

Authentication verifies client identity.

Only authenticated requests may access protected endpoints.

Authentication mechanisms should remain replaceable without affecting API contracts.


---

## Authorization

Authorization verifies permissions.

Permissions should be evaluated before backend service invocation.

Authorization decisions should remain independent of transport protocols and API endpoint implementations.

---

## Access Control

Access policies should remain centralized.

Authorization rules should remain independent of individual API endpoints.

---

# 13. Performance Considerations

The API should minimize communication overhead while preserving correctness.

---

## Stateless Requests

Every request should remain self-contained.

API servers should not depend on local request state.

---

## Response Size

Responses should include only necessary information.

Unnecessary payload increases latency.

---

## Pagination

Large collections should support pagination.

Pagination improves scalability and response consistency.

---

## Rate Limiting

The API may apply request limits to protect backend services.

Rate limiting should remain configurable.

---

## Response Caching

Cacheable responses may be reused when business consistency permits.

Caching policies should remain configurable.

Cached responses should never violate data consistency.

Response caching is an implementation optimization.

Caching should never alter API semantics, consistency guarantees or ownership rules defined by the backend architecture.

Clients should not depend on cached behavior.

---

# 14. API Contract Stability

Public API contracts should remain stable whenever possible.

Internal backend evolution should not require unnecessary client changes.

Stable contracts reduce integration cost and improve long-term maintainability.

---

# 14a. Contract Synchronization

The API contract exists in one authoritative, machine-readable form: the published contract artifact **`docs/api/openapi.json`**, generated from the running application (`backend/scripts/export_openapi.py`).

- An architecture check fails whenever the committed artifact diverges from the application, so every contract change is explicit and reviewable — never silent.
- Consumers **derive** from the artifact instead of hand-maintaining copies: frontend communication types and mock definitions are derivation targets (derivation tooling is deferred implementation work; the artifact is its fixed source).
- Hand-written consumer copies are transitional; a divergence between a consumer copy and the artifact is a consumer defect, not a contract ambiguity.

This resolves the multiple-hand-written-copies risk (backend schemas, frontend DTOs, mocks) identified by the architecture audit (E-05).

---

# 15. Future Evolution

Future API capabilities may include:

- GraphQL support
- gRPC interfaces
- streaming responses
- webhook integration
- asynchronous APIs
- API gateway integration

Future capabilities should extend communication mechanisms without changing backend service responsibilities.

---

# 16. Design Principles Applied

The API follows the engineering principles established throughout SentinelAI.

| Principle | API Application |
|-----------|-----------------|
| Separation of Responsibilities | Business logic remains within backend services. |
| Single Source of Truth | Backend services remain authoritative for business data. |
| Explainability | Responses preserve request identifiers and execution metadata. |
| Technology Independence | API behavior remains independent of HTTP frameworks. |
| Scalability | Stateless communication enables horizontal scaling. |
| Modularity | API responsibilities remain isolated from backend implementation. |
| Architecture Before Framework | API contracts are defined before implementation technologies. |

---

# Closing Statement

The SentinelAI API provides a stable and maintainable communication layer between client applications and backend services.

By limiting API responsibilities to communication, validation and delegation, the platform preserves clean architectural boundaries while supporting secure and scalable interaction.

Future implementations may adopt different communication technologies.

However, the architectural responsibilities defined in this document should remain stable regardless of implementation details.

---

# Version History

| Version | Date | Description |
|----------|------------|--------------------------------|
| 1.0.0 | 2026-06-26 | Initial API Design specification created |
| 1.1.0 | 2026-07-03 | Planner delegation aligned with the single-action control model (ADR-010); Workflow Resource replaced by the Planner Action Resource |
| 1.2.0 | 2026-07-03 | Contract Synchronization defined (§14a): committed OpenAPI artifact as the single contract source with freshness enforcement; consumer copies become derivation targets (audit finding E-05) |
| 1.3.0 | 2026-07-04 | Investigation Run Resource added (investigation-level Investigation Loop surface, ADR-010/ADR-013); the transitional Planner Action Resource removed as its documented supersession (ES-044, slice decision V-2) |