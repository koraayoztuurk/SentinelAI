# SentinelAI Implementation Tracker

> Internal development tracker.
> This document is NOT part of the project documentation.
> It exists to preserve implementation decisions, review standards and development continuity throughout the project.

---

# Project Status

| ES | Task | Status |
|----|------|--------|
| ES-001 | Repository Foundation | ✅ Completed |
| ES-002 | Backend Architecture Skeleton | ✅ Completed |
| ES-003 | Domain Model | ✅ Completed |
| ES-004 | Persistence Foundation | ✅ Completed |
| ES-005 | Investigation Service | ✅ Completed |
| ES-006 | Graph Service | ✅ Completed |
| ES-007 | Memory Service | ✅ Completed |
| ES-008 | Planner Service | ✅ Completed |
| ES-009 | AI Foundation | ✅ Completed |
| ES-010 | Agent Runtime | ✅ Completed |
| ES-011 | Planner Agent | ✅ Completed |
| ES-012 | Memory Manager | ✅ Completed |
| ES-013 | RAG Pipeline | ✅ Completed |
| ES-014 | API Foundation | ✅ Completed |
| ES-015 | Investigation API | ✅ Completed |
| ES-016 | Graph API | ✅ Completed |
| ES-017 | Memory API | ✅ Completed |
| ES-018 | Planner API | ✅ Completed |
| ES-019 | Authentication | ✅ Completed |
| ES-020 | Authorization | ✅ Completed |
| ES-021 | Audit | ✅ Completed |
| ES-022 | Secrets | ✅ Completed |
| ES-023 | Frontend Foundation | ✅ Completed |
| ES-024 | Dashboard | ✅ Completed |
| ES-025 | Investigation Workspace | ✅ Completed |
| ES-026 | Graph Visualization | ✅ Completed |
| ES-027 | State Management | ✅ Completed |
| ES-028 | Docker | ✅ Completed |
| ES-029 | Configuration | ✅ Completed |
| ES-030 | Deployment | ✅ Completed |
| ES-031 | Observability | ✅ Completed |
| ES-032 | Test Foundation | ✅ Completed |
| ES-033 | Architecture Tests | ✅ Completed |
| ES-034 | Integration Tests | ✅ Completed |
| ES-035 | AI Validation | ✅ Completed |
| ES-036 | Performance & Reliability | ✅ Completed |
| ES-037 | AI Composition (Investigation Loop & Retrieval Flow) | ✅ Completed |
| ES-038 | Audit Remediation Phase 2 (Governance & Doc Alignment) | ✅ Completed |
| ES-039 | Gap Closure (Trace, Resilience, Propagation, Governance) | ✅ Completed |
| ES-040 | PostgreSQL Persistence Foundation & Investigation-Family Adapters | ✅ Completed |
| ES-041 | PostgreSQL Memory Adapter (Versioned MemoryItem) | ✅ Completed |
| ES-042 | Runtime Persistence Binding (DI) | ✅ Completed |
| ES-043 | Concrete LLM Provider Adapter (Google Gemini) | ✅ Completed |
| ES-044 | Investigation Loop Runtime Wiring & Run Surface | ✅ Completed |
| ES-045 | Trace & Outcome Read API | ✅ Completed |
| ES-046 | Dev-Grade Authentication + Owner-Scoped Authorization + Operation Context | ✅ Completed |
| ES-047 | Frontend Live Flow (Mock-Free) & Slice Closure | ✅ Completed |
| ES-048 | Neo4j Graph Persistence: Migration Mechanism + Authoritative Adapter + Runtime Binding | ✅ Completed |
| ES-049 | Application-Owned Embedding Port + Concrete Gemini Embedding Adapter | ✅ Completed |
| ES-050 | Transactional Outbox + Idempotent Embedding Projector + Qdrant | ✅ Completed |
| ES-051 | Live RAG Retrieval: Concrete Source-Backed Retriever + Run-Path Consumption | ✅ Completed |
| ES-052 | Investigation-Scoped Memory Surface (Memory Listing API + Workspace Memory Region) | ✅ Completed |
| ES-053 | Seed Utility & Second-Slice Demo (Milestone A closed) | ✅ Completed |
| ES-054 | NVIDIA NIM LLM Provider (MiniMax-M3) + LLM Provider Selection + Dev Auto Sign-In | ✅ Completed |
| ES-055 | Decision Engine: Outcome Synthesis on Completed Runs + Outcome Panel | ✅ Completed |
| ES-056 | Validation Agent: Findings Assessment Before Synthesis | ✅ Completed |
| ES-057 | Graph Analysis Agent: Neighbourhood Analysis Enriching the Run (Milestone B closed) | ✅ Completed |
| ES-058 | External Knowledge Live: ATT&CK Catalog + NVD CVE Providers + EXTERNAL Retrieval Strategy | ✅ Completed |
| ES-059 | Threat Intelligence Agent: External Correlation Enriching the Run (Milestone C closed) | ✅ Completed |
| ES-060 | Evidence Payload Store: RFC-001 + ADR-015 + Content-Addressed Port/Adapter + Payload REST | ✅ Completed |
| ES-061 | Workspace Evidence Payload Upload/Download + Milestone D Close | ✅ Completed |
| ES-062 | Production Identity Provider: JWT Authenticator + AUTH_PROVIDER Selection + owner==subject on Create | ✅ Completed |
| ES-063 | Multi-Tenancy: RFC-002 + ADR-016 + Investigation Tenant Scope + Tenant-Aware Authorizer (Milestone E closed) | ✅ Completed |

---

# Permanent Engineering Decisions

These decisions have already been made.
Do not revisit them unless the architecture documentation changes.

---

## Data Ownership Map

The ownership of business data is fixed unless the architecture documentation explicitly changes.

| Technology | Owns |
|------------|------|
| PostgreSQL | Investigation, Evidence, Finding, Report, Task, MemoryItem |
| Neo4j | Entity, Relationship |
| Qdrant | Memory Embeddings (non-authoritative) |
| Redis | Cache only (non-authoritative) |

Service ownership:

- Investigation Service → Investigation, Evidence, Finding, Report
- Graph Service → Entity, Relationship
- Memory Service → MemoryItem and semantic embeddings
- Planner Service → Workflow orchestration only

Each backend service owns its persistence schema inside the shared PostgreSQL instance.

No service may directly access another service's persistence layer.

---

## Repository Architecture

Repository responsibilities are intentionally split across two layers.

- The generic `Repository` marker lives in the Domain layer.
- Repository contracts live in the Application layer.
- Infrastructure provides the concrete implementations.
- Backend services depend only on repository contracts.

Repository contracts should remain minimal and should expose only operations required by the owning service.

Generic CRUD repositories are intentionally avoided.

---

## Architecture

- Clean Architecture.
- Layer dependencies always point inward.
- Domain remains technology-independent.
- Infrastructure depends on abstractions.
- Backend services own business logic.
- API remains a thin communication layer.

---

## Domain

- Caller supplies identifiers.
- Caller supplies timestamps.
- No clock abstraction.
- No UUID generation inside services.
- Typed identifiers are used.
- Open string value objects instead of closed enums where appropriate.
- Domain is never modified unless documentation explicitly requires it.

---

## Persistence

- Repository ports live in the Application layer.
- Infrastructure implements repository ports.
- Redis is cache only.
- Redis is never authoritative.
- PostgreSQL remains the source of truth.
- Repository contracts stay minimal.
- No generic CRUD repositories.
- One service operation = one local transaction.

---

## Services

- Business validation belongs to services.
- Controllers never implement business logic.
- Services never access infrastructure directly.
- Services depend only on repository contracts.

---

## General

- Simplicity before abstraction.
- No speculative abstractions.
- No unnecessary base classes.
- No service locator.
- No undocumented business rules.
- No undocumented architectural responsibilities.

---

## Standard Implementation Patterns

The following implementation patterns are considered project standards.

### Value Objects

- frozen dataclasses
- slots enabled
- standalone implementations
- no inheritance hierarchy

### Repository Contracts

- async Protocol
- minimal documented methods
- no generic CRUD abstraction

### Exceptions

- inherit from SentinelAIError
- stable dotted error codes
- define only documented business failures

### Services

- thin public methods
- private helper methods for validation
- repository-driven state
- no internal caching

### Tests

- plain test functions
- no pytest fixtures
- in-memory test doubles
- deterministic inputs

---

# Claude Prompt Standard

Every implementation task follows the same workflow.

1. Read required documentation.
2. Discover additional relevant documentation.
3. Produce an implementation plan.
4. Wait for approval.
5. Implement.
6. Run:
   - ruff
   - mypy (strict)
   - pytest
7. Perform self-review.
8. Produce Documentation Improvement Recommendations.

---

# Review Checklist

Every implementation is reviewed for:

- Scope compliance
- Architectural compliance
- Dependency direction
- Simplicity
- Overengineering
- Business rules invented?
- Architectural responsibilities invented?
- Documentation gaps discovered?
- Tests included?
- Verification completed?

---

# Documentation Improvements Already Applied

## database-architecture.md

- Redis architecture
- Cache ownership
- Cache lifetime
- Cache failure strategy
- Supporting persistence technologies

## api-design.md

- Repository abstraction clarification
- Persistence transparency
- Storage-independent error handling
- Response caching clarification

## configuration-management.md

- Domain configuration examples
- Configuration grouping by responsibility

## frontend-architecture.md (ES-030, v1.1.0)

- Server-state (cached backend data) clarified as a distinct concern from the four owned client-state categories

## ui-state-management.md (ES-030, v1.1.0)

- Cached backend (server) state noted as managed separately from the four state categories

## investigation-workspace.md (ES-030, v1.1.0)

- Timeline event source clarified (reconstructed from investigation-artifact timestamps)
- AI Insights / Memory region data dependency clarified (awaiting Application Domain / AI Runtime exposure)

## visualization-architecture.md (ES-030, v1.1.0)

- Graph clarified as an entity-seeded neighbourhood (seeded from investigation-scoped entities)

## ADR-010 (ES-037, new)

- Planner composition decided: Planner Agent (AI Runtime, decides) + Planner Service (Application,
  executes one action per request); the Planner Service is an **orchestration seam**, amending ADR-004
- Composition ownership decided: the AI Runtime owns the Investigation Loop and the Retrieval Flow
- Dependency direction decided: AI Runtime → Application, one-way (resolves the ADR-005 ambiguity)
- Single-action control model made normative

## planner-service.md (ES-037, v2.0.0)

- Rewritten around the single-action control model; the stateful multi-step workflow orchestration
  content (start/pause/resume/cancel operations, workflow lifecycle store, dependency validation,
  parallel execution, workflow recovery) removed instead of disclaimed
- Caller (AI Runtime Investigation Loop) and statelessness stated once, coherently

## api-design.md (ES-037, v1.1.0)

- Planner routing/delegation aligned with the single-action model (ADR-010)
- "Workflow Resource" replaced by the "Planner Action Resource"; its public exposure marked transitional

## architecture-testing.md (ES-037, v1.1.0)

- Normative **Architectural Constraint Catalogue** added (AC-01…AC-13) — the concrete constraint list
  the platform enforces, with per-constraint source and verification status
- The catalogue is declared the authoritative source of concrete constraints; this tracker's
  "Permanent Engineering Decisions" and the test suites now **mirror** it (normative-source drift fix)

## ADR-011 (ES-038, new)

- Supporting-persistence category introduced (never authoritative, reproducible, availability-independent);
  Redis governed under it with demand-driven integration — closes the "Redis without an ADR" gap (audit A3);
  amends ADR-003

## database-architecture.md (ES-038, v1.1.0)

- Synchronization scoped to derived representations with **named service ownership** (Memory Service owns
  embedding sync); the undefined "SyncService" removed; Neo4j no longer depicted as a sync target
  (it is authoritative for graph objects) — audit A4
- **§8a Cross-Store References** added: identifiers as the only cross-store mechanism, validation through
  the owning service, eventual consistency, observable dangling references

## rag-architecture.md (ES-038, v1.1.0) & memory-architecture.md (ES-038, v1.1.0)

- Memory Agent aligned across both documents with the implemented **strategy-selector** model (produces
  one Retrieval Plan; retrieval/coordination/assembly belong to the pipeline; composition = Retrieval Flow,
  ADR-010) — closes audit A5/B5 (the previously code-comment-only deviation)

## domain-model.md (ES-038, v1.1.0) & investigation-service.md (ES-038, v1.1.0)

- Finding lifecycle §6/§15 inconsistency fixed (Accepted added to the state list) — audit B10
- Investigation lifecycle completed: **Active ↔ Suspended**, **Suspended → Archived**,
  **Completed → Active (reopen, planner-agent §10)**; "close Investigation" clarified as completing
  (no separate Closed state) — resolves the open gaps "SUSPENDED state transition definition" and
  "Investigation 'Close' lifecycle state"; realized in `InvestigationService._ALLOWED_TRANSITIONS` + tests
- `domain/enums.py` module note about documentation inconsistency removed (now consistent)

## dashboard-architecture.md (ES-038, v1.1.0)

- "Confirmed finding" defined normatively (**Validated or Accepted**) with explicit ownership: a
  presentation filter over domain lifecycle states, realized in the frontend communication layer — audit B8

## agent-architecture.md (ES-038, v1.1.0) & planner-agent.md (ES-038, v1.1.0)

- "Investigation Workspace" terminology disambiguated: Application Domain investigation-context capability
  (Investigation Service, ADR-004) vs the frontend page vs the State Assembler port (ADR-010) — audit A10

## api-design.md (ES-038, addition to v1.1.0)

- Planner Action Resource contract status made explicit: **transitional, not part of the stable public
  API**, no compatibility commitment, external clients driving raw actions unsupported (audit B3); mirrored
  in the planner router docstring

## ADR README (ES-038)

- Rationale standard strengthened: decision-specific drivers required, generic quality attributes
  insufficient, a measurable/checkable consequence expected (ADR-010 onward) — audit A7
- ADR-011 added to the index

## README.md (ES-038)

- Technology table: "AI Runtime — LangGraph, LangChain" replaced with the provider-neutral, in-process
  runtime actually decided (ADR-005/ADR-010) — audit A9

## ADR-012 / ADR-013 / ADR-014 (ES-039, new)

- **ADR-012** Derived Representation Production and Propagation: transactional outbox + idempotent
  projectors; **no request path writes to two stores** (AC-14); embedding port owned by the
  application layer, implemented in infrastructure (gaps E-01 + D-01)
- **ADR-013** AI Provider Resilience and the Single Agent Execution Path: bounded provider execution
  time as port contract; typed generic Agent contract with the Agent Runtime as the only execution
  host; loop degrade-to-escalation on agent failure; circuit breaker as concrete-provider concern
  (gaps E-02 + D-03)
- **ADR-014** Lightweight Architectural Proposal Process: RFC required only above an explicit
  threshold (supersede/amend ADRs, boundary/constraint/domain-semantics changes, new service or
  persistence category); single-page form; ADR Proposed→Accepted as the default discussion stage
  (gaps M-06 + D-04)

## Documentation (ES-039)

- domain-model v1.2.0 — Trace Entry §11b (Investigation Trace, append-only explainability journal;
  gaps M-01/E-07); Investigation owns Trace Entries
- investigation-service v1.2.0 — Outcome operations (0..1 per investigation; gaps M-07), Trace
  operations, evidence ingestion boundary (attachment here; ingestion/normalization a future
  capability needing its own decision; gaps M-02)
- database-architecture v1.2.0 — ADR-012 mechanism section; §8b Evidence Payload Storage
  (content-addressed object store designated, inline content accepted interim; gaps M-02)
- memory-service v1.1.0 — outbox-mediated async memory-creation flow (no dual-write); embedding port
  ownership (AC-04-compatible)
- graph-service v1.1.0 — §11a versioned graph migrations + canonical relationship/entity-type
  vocabulary ownership (gaps E-03)
- authentication-authorization v1.1.0 — §6a Investigation Access Scoping Model (owner-based,
  extensible; shared-knowledge boundary at promotion; gaps M-04) + §6b Operation Context (gaps E-06)
- **data-lifecycle.md (new)** — retention/erasure architecture: lifecycle ownership per category,
  deprecation≠deletion, tombstoning/crypto-shredding categories, audit exception (gaps M-05)
- api-design v1.2.0 — §14a Contract Synchronization: committed `docs/api/openapi.json` artifact +
  freshness enforcement (gaps E-05)
- agent-architecture v1.2.0 — typed result envelope (single execution path), provider resilience
  contract, external knowledge provider interface
- rag-architecture v1.2.0 — external retrieval bound to the External Knowledge port (gaps M-03/E-04)
- architecture-testing v1.2.0 — AC-14 declared (no dual-write), AC-15 enforced (contract freshness)
- roadmap v1.1.0 — **Vertical Slice First** normative execution rule (gaps D-02) + Delivery Record
  public mirror (gaps D-05)
- rfc README v1.1.0 — ADR-014 threshold + single-page form made normative

---

# Deferred Decisions

The following are intentionally NOT implemented.

- Investigation Summary
- Evidence Detach
- Report Lifecycle
- Report Archival
- Investigation/Finding Type
- Audit implementation
- Distributed transactions
- Cross-service orchestration
- AI reasoning
- Graph analytics
- Memory reasoning
- ThreatGraph — the investigation-oriented graph utilization layer (ADR-007). Recorded here by the
  architecture audit (finding B6): the concept was decided but had no implementation and no tracking
  entry. It remains intentionally unimplemented until the graph reasoning capabilities that consume it
  (Graph Analysis Agent, attack-path analysis) are specified. ADR-007 remains Accepted.

---

# Open Documentation Gaps

The following architecture questions have already been discovered.

Do not resolve them through implementation.

They require documentation updates.

- Investigation Summary definition
- Evidence Detach semantics
- Report lifecycle
- Investigation/Finding type definition
- Investigation "Close" lifecycle state
- Audit lifecycle specification
- SUSPENDED state transition definition
- Task service ownership

---

# Technical Debt

The following items are intentionally deferred implementation work rather than missing functionality.

## ES-004

- PostgreSQL repository implementations
- Neo4j repository implementations
- Qdrant repository implementations
- Redis cache integration

Reason:
Infrastructure foundation was completed before concrete persistence adapters.

---

## ES-005

- Investigation PostgreSQL adapter
- ORM models
- Entity mappers
- Live database integration tests

Reason:
The Investigation Service is currently verified through in-memory repository implementations only.

These items are expected to be completed during the persistence implementation tasks.

---

## ES-006

- Neo4j GraphRepository adapter (driver-backed implementation)
- Graph schema bootstrap (constraints / indexes)
- Entity merge / resolution beyond identifier equality
- Entity deprecation (no domain field exists)
- Advanced traversal: shortest path, attack path, relationship expansion
- Graph statistics
- Live Neo4j integration tests

Reason:
The Graph Service is verified through an in-memory graph repository only. Graph-specific
traversal and entity-resolution semantics are deferred until documented and until the Neo4j
adapter is implemented.

---

## ES-007

- PostgreSQL MemoryItem adapter (driver-backed implementation, ORM models, mappers)
- Embedding provider port + vector-store port
- Semantic retrieval, embedding management and synchronization operations
- Memory archival status (no ARCHIVED status exists in the domain)
- Metadata retrieval (tags / investigation type — no such fields in the domain)
- Live PostgreSQL integration tests

Reason:
The Memory Service is verified through an in-memory repository only. Embedding/semantic/sync
operations depend on an embedding provider (AI) that does not yet exist and are deferred to the
AI/RAG specifications (ES-009/013).

---

## ES-008

- Full Planner Action catalogue (only a representative set of service operations is implemented)
- Execution constraints: timeout and retry semantics
- Live wiring of the Planner Service into the API / dependency-injection layer

Reason:
The Planner Service implements a representative, typed action set; the full operation catalogue is
deferred until the Planner Agent (ES-011) defines its action vocabulary. Timeout/retry and live
wiring are introduced by later specifications.

---

## ES-009

- Concrete LLM and embedding provider adapters (external/edge implementations)
- AI provider configuration (provider/model selection, API keys)
- Richer LLM contract shapes: messages/roles, streaming, structured output
- Batch embedding
- AI Runtime wiring (DI / lifecycle) and the higher AI layers (agent host, Decision Engine, RAG)

Reason:
The AI Foundation defines only the provider-neutral provider ports and the AI error base. Everything
with no consumer yet is deferred to the tasks that introduce concrete providers and the higher AI
layers (ES-010/011/012/013).

---

## ES-010

- Concrete agents (Planner Agent ES-011, Memory Manager ES-012, specialized agents)
- Tool-access model and the Decision Engine
- Agent execution metadata (duration, tools used, memory accessed) and the AI Runtime timing approach
- Rich agent context/output shapes (full investigation context/state; structured findings/confidence/evidence references)
- Provider injection into concrete agents; AI Runtime wiring (DI / lifecycle)

Reason:
The Agent Runtime defines only the agent contract and the stateless execution host. Everything with
no consumer yet is deferred to the tasks that introduce concrete agents and the higher AI layers.

---

## ES-011

- Generic AgentRuntime/AgentResult bridge for the Planner Agent (typed `decide` runs standalone; not yet wired through the neutral runtime)
- Full Planner Action vocabulary (only control + id-based actions are emitted; create/mutation deferred)
- Richer reasoning and the concrete LLM provider (tested with a fake; prompt content minimal)
- Investigation State assembly (the Workspace/Context Builder that produces the consumed state)

Reason:
The Planner Agent implements the typed `decide(InvestigationState) -> PlannerAction` contract over a
fake-tested LLM provider. The generic-runtime bridge, full action vocabulary, real reasoning/provider
and state assembly are introduced by later specifications.

---

## ES-012

- Real Retriever and knowledge-source coordination (the Memory Agent selects strategies; it does not
  retrieve)
- Context Builder / Context Validation / Prompt Builder (the RAG context pipeline)
- Semantic / graph / external retrieval execution and embeddings/vector store
- Generic AgentRuntime/AgentResult bridge for the Memory Agent (typed `plan` runs standalone)
- Strategy *execution* (turning a selected strategy into actual retrieval) and the full strategy
  behaviour
- Richer reasoning and the concrete LLM provider (tested with a fake; prompt content minimal)

Reason:
The Memory Agent implements the typed `plan(InvestigationState, RetrievalPlanId) -> RetrievalPlan`
strategy-selection contract over a fake-tested LLM provider. Actual retrieval, source coordination and
context assembly belong to the RAG Pipeline (ES-013); the generic-runtime bridge and a real
reasoning/provider are introduced by later specifications.

---

## ES-013

- Concrete source-backed retrievers: semantic retrieval (the vector-store port/adapter and embedding
  usage), structured retrieval via the Memory Service, graph retrieval via the Graph Service, and
  external-intelligence retrieval (the Retriever is a port; only an in-memory double exists)
- Conflict detection and resolution (rag §9): only exact `(source, reference)` duplicates are collapsed
- Context compression, context budget and prioritization/ranking (rag §16)
- Memory Agent ↔ pipeline composition (a top-level orchestrator that runs the Memory Agent then the
  pipeline) and Planner wiring
- Generation: the pipeline produces a provider-neutral `Prompt`; the actual LLM call belongs to the
  consuming agent (rag §19)
- Live DI/lifecycle wiring of the pipeline

Reason:
The RAG Pipeline implements the full context-engineering core (Retriever port → Context Builder →
Context Validation → Prompt Builder) with retrieval abstracted behind a single replaceable port.
Concrete retrieval sources, richer context engineering (conflict/compression/budget) and generation are
introduced by later specifications.

---

## ES-014

- Authentication and authorization (api-design §12) — deferred to ES-019/020; the request lifecycle is
  foundation-only (request context + envelope) for now
- Rate limiting, request throttling and abuse detection (api-design §10/§13)
- Pagination for large collections (api-design §13)
- Response caching (api-design §13)
- Processing-duration in the response envelope (currently exposed via the `X-Process-Time` header only)
- Resource endpoints and service delegation (the `/api/v1` router is empty) — introduced by ES-015+

Reason:
The API Foundation establishes only the cross-cutting HTTP layer: the versioned router, the request
context (request/correlation identifiers), the standard success/error envelope and request-id-bearing
error translation. Security, traffic management, pagination, caching and the resource endpoints belong
to later specifications.

---

## ES-015

- Investigation persistence runtime binding: `get_investigation_service` raises `ServiceNotConfiguredError`
  (503) until the concrete repository adapter (ES-005 technical debt) exists; tests bind in-memory doubles
  via `dependency_overrides`
- Pagination for the list endpoints (api-design §13)
- A single-finding GET endpoint (the Investigation Service exposes no `get_finding`)
- Enriched request-validation error detail (the `RequestValidationError` handler returns a generic
  message without per-field details)
- Authentication and authorization on the endpoints (ES-019/020)

Reason:
The Investigation API is the thin presentation layer over the Investigation Service: controllers,
schemas/mappers, the id/clock generators and error translation. The concrete persistence binding,
pagination, auth and richer validation reporting belong to later specifications.

---

## ES-016

- Graph persistence runtime binding: `get_graph_service` raises `ServiceNotConfiguredError` (503) until
  the concrete Neo4j adapter (ES-006 technical debt) exists; tests bind an in-memory `GraphRepository`
  double via `dependency_overrides`
- Real neighbourhood-traversal semantics (depth/max_nodes behaviour) — the in-memory test double is
  minimal; the documented traversal belongs to the Graph Service / Neo4j adapter
- A create-vs-reuse signal on `create_entity` (the frozen ES-006 contract does not expose one, so the
  API returns a uniform 201 and reuse is transparent)
- Pagination for the list endpoints (api-design §13)
- Authentication and authorization on the endpoints (ES-019/020)

Reason:
The Graph API is the thin presentation layer over the Graph Service: controllers, schemas/mappers and
error translation, reusing the ES-014/015 foundation. The concrete persistence binding, real traversal,
pagination and auth belong to later specifications.

---

## ES-017

- Memory persistence runtime binding: `get_memory_service` raises `ServiceNotConfiguredError` (503) until
  the concrete PostgreSQL MemoryItem adapter (ES-007 technical debt) exists; tests bind an in-memory
  `MemoryRepository` double via `dependency_overrides`
- Embedding / semantic-retrieval API surface (out of REST scope; belongs to the AI/RAG specifications,
  ES-007/013)
- Pagination for the history endpoint (api-design §13)
- Authentication and authorization on the endpoints (ES-019/020)

Reason:
The Memory API is the thin presentation layer over the Memory Service: controllers, schemas/mappers and
error translation, reusing the ES-014/015/016 foundation. The concrete persistence binding, semantic
retrieval, pagination and auth belong to later specifications.

---

## ES-018

- Planner runtime binding: `get_planner_service` raises `ServiceNotConfiguredError` (503) — the Planner
  Service depends on the Investigation/Graph/Memory services whose persistence adapters are all deferred
  (ES-005/006/007 TD); tests bind an in-memory-backed Planner Service via `dependency_overrides`
- The `Create*` Planner Actions (CreateInvestigation/Entity/Relationship/Memory) — they embed full domain
  objects and duplicate the resource POST APIs; the full action catalogue remains deferred (ES-008 TD)
- The Planner Agent's iterative multi-step decision loop as an API (an AI-layer concern, not the
  single-action Planner Service)
- Pagination and authentication/authorization on the endpoint (ES-019/020)

Reason:
The Planner API is the thin presentation layer over the single-action Planner Service: one execute
endpoint, the discriminated-union action request, the generic execution-result envelope and error
translation, reusing the ES-014/015 foundation. The full action catalogue, the agent loop, persistence
binding and auth belong to later specifications.

---

## ES-019

- Concrete identity provider/adapter (JWT / OAuth / session) — the `Authenticator` port is defined but the
  only implementation is the default-deny `UnconfiguredAuthenticator`; a real provider depends on the
  Secrets specification (ES-022)
- Authorization enforcement (permission evaluation in the Application Domain) and the mechanism by which
  the `AuthenticatedIdentity` flows from the boundary to backend services (ES-020)
- System / external identity issuance, token continuity / refresh, and `WWW-Authenticate` challenge
  semantics

Reason:
ES-019 establishes only identity verification at the API boundary: the identity model, the replaceable
`Authenticator` port, the default-deny enforcement seam and the 401 translation. Concrete providers,
authorization and identity propagation to services belong to later specifications.

---

## ES-020

- The concrete authorization policy (role / permission taxonomy, resource and investigation ownership,
  context-aware decisions) — only the default-deny `DenyAllAuthorizer` exists; the `Authorizer` port is
  ready for a real policy
- Per-resource-service authorization (the documented "resource-owning service authorizes") — ES-020 uses a
  central application authorizer triggered at the API boundary with a coarse `method + path` operation
- Flow of the authorization decision into the audit trail (ES-021) and policy configuration / secrets
  (ES-022)

Reason:
ES-020 establishes only the authorization decision contract and its enforcement: the application-layer
`Authorizer` port, the `AuthorizationRequest` it evaluates, the default-deny `DenyAllAuthorizer` (403) and
the boundary seam that triggers it. The concrete policy, per-service enforcement and audit/secret
integration belong to later specifications.

---

## ES-021

- The durable, tamper-resistant append-only audit store with retention and non-repudiation guarantees —
  only the default `LoggingAuditRecorder` exists; the `AuditRecorder` port is ready for a real sink (the
  "Audit lifecycle specification" documentation gap)
- Per-business-operation semantic audit recorded inside the services (the central middleware records a
  coarse operation event with outcome derived from the HTTP status)
- The Investigation / Administrative / System audit action categories (only the three actions ES-021 emits
  are modelled), and AI Runtime audit contribution
- Audit sink configuration / secrets (ES-022)

Reason:
ES-021 establishes only the audit capability and its boundary integration: the `AuditEvent` model, the
`AuditRecorder` port, the default `LoggingAuditRecorder` and the best-effort `AuditMiddleware` that reads
the request state. The durable store, richer categories, per-service audit and configuration belong to
later specifications.

---

## ES-022

- The concrete durable secret store / vault adapter (and an async `resolve` variant) — only the default
  `EnvironmentSecretProvider` exists; the `SecretProvider` port is ready for a real store
- The runtime secret-lifecycle mechanism (rotation / revocation / retirement) — only the architectural
  lifecycle is modelled, not a runtime mechanism
- Secret-consuming adapter wiring: the deferred AI provider API keys (ES-009) and the deferred
  authentication provider (ES-019) will consume secrets through the `SecretProvider`
- Traceable secret usage with consumer/identity context, and the human/external secret categories

Reason:
ES-022 establishes only the technology-independent secrets foundation: the `Secret` protection primitive,
the typed `SecretName`, the `SecretProvider` port, the default `EnvironmentSecretProvider` and
`SecretNotFoundError`. The concrete vault, the lifecycle mechanism and the secret-consuming adapters belong
to later specifications (no live consumer exists yet, mirroring the ES-009 foundation).

---

## ES-023

- The business pages: Investigation Dashboard (ES-024), Investigation Workspace (ES-025) and Graph
  Visualization (ES-026) — the foundation ships only the app shell and a single placeholder route
- The server-state / cache library (TanStack Query) and the global client store (State Management, ES-027) —
  the foundation provides a stateless typed `apiClient` and a minimal `state/` directory
- The concrete authentication / login flow and token storage — the `apiClient` reads the bearer token from
  a pluggable `getAuthToken()` source; the real flow integrates with ES-019 later
- Design-system depth on the primitive UI (`Button` is minimal — children/onClick/disabled/className; no
  variant/size/theme), and i18n / theming / accessibility hardening / per-route lazy loading & virtualization

Reason:
ES-023 establishes only the frontend foundation: the React + TypeScript + Vite + Tailwind project, the
layered architecture skeleton, the Communication layer (`apiClient`) as the single Backend API boundary, the
app shell and the lint/typecheck/test/build discipline. The business pages, state library, authentication
flow and design-system depth belong to later specifications.

---

## ES-024

- Backend data sources for three dashboard components: Active Objectives, AI Insights and Recent Activity
  render explicit "not yet available" placeholders — the backend exposes no objectives/insights/activity
  endpoints yet
- Server-state cache / auto-refresh (the dashboard uses a minimal local fetch hook; TanStack Query is
  ES-027) and the dashboard refresh model (§9)
- Investigation-list / platform dashboard (the backend has no list-investigations endpoint) and deep-linking
  into detailed workspace regions (ES-025)
- MSW node request interception in the jsdom test environment (unreliable on this runtime): the page
  integration tests mock the communication loader directly; MSW still powers the dev browser demo
- camelCase model mapping breadth and the real authentication token flow (ES-019 integration)

Reason:
ES-024 delivers the Investigation Dashboard presentation over the ES-023 communication layer: the page,
sections/components, a view-model mapper and a minimal fetch hook. The missing backend data sources, the
server-state library, the platform dashboard and richer test interception belong to later specifications.

---

## ES-025

- Server-state cache / auto-refresh and the promoted global client store (the workspace uses a minimal
  local fetch hook + a page-scoped React-context Investigation Context) — State Management (ES-027)
- Graph Region: rendered as a placeholder — the graph visualization is delivered by ES-026
- AI Insights and Memory Regions: explicit "not yet available" placeholders — the backend exposes no
  investigation-scoped insights source and no list-memory-by-investigation endpoint
- The full Workspace Event Model (investigation-workspace §8) and richer interaction types
  (focus/drill-down/context-inspection, interaction-model §5) — only selection + the derived
  finding→evidence highlight are implemented
- The canonical "investigation event" source for the Timeline (the timeline is Derived State from
  evidence/finding timestamps only) — a documentation gap
- The real authentication token flow (ES-019 integration)

Reason:
ES-025 delivers the Investigation Workspace presentation: the workspace page, its coordinated regions
(Overview/Evidence/Timeline/Findings + placeholders), the workspace view model (extending the ES-024
`DashboardViewModel`) with pure derivations, and a minimal presentation-only Investigation Context.
The server-state library, the global store, the graph visualization, the full event model and the
missing backend data sources belong to later specifications.

---

## ES-026

- Advanced graph rendering: force-directed / interactive layout, zoom & pan, node dragging and collision
  handling (the layout is a deterministic radial ego-graph)
- Multi-hop traversal and attack-path / shortest-path visualization (the neighbourhood is a single hop —
  `depth=1`); server-side traversal semantics remain in the Graph Service / Neo4j adapter (backend ES-006 TD)
- An investigation-scoped graph/entity-listing endpoint (the seeds are derived from the confirmed findings'
  `related_entities` because the backend Graph API is entity-seeded) — a documentation gap
- Entity↔timeline/evidence cross-region highlighting (entity selection re-centers the graph but does not yet
  highlight other regions; the entity→event mapping is undocumented) and relationship-detail inspection
- Server-state cache / auto-refresh and the promoted global store — State Management (ES-027)
- The concrete Neo4j-backed graph data at runtime (the Graph Service is unbound → 503; MSW serves the graph
  in the dev demo, mirroring ES-024/025)

Reason:
ES-026 delivers the Graph Visualization region: the entity-seeded SVG ego-graph, its communication layer
(`graph.ts` DTOs/loader + pure `toGraphViewModel`/layout helpers) and the seed/focus extension of the
Investigation Context. Rich layout/interaction, multi-hop analytics, cross-region entity synchronization and
the live persistence binding belong to later specifications and the backend graph technical debt.

---

## ES-027

- Mutations / optimistic updates and real invalidation triggers: the invalidate helpers exist and back the
  retry buttons, but there is no write flow yet (the backend services are unbound → 503; MSW is read-only)
- View State persistence (panel visibility / sorting) — View State stays region-local, ephemeral `useState`;
  no persisted View State is introduced
- Session State breadth and its persistence contract: only `theme` exists (localStorage); language /
  notification / workspace-personalization preferences and a backend-backed profile are deferred
- Lifting the Investigation Context above the workspace page (it stays workspace-scoped; there is a single
  workspace route, so cross-page selection persistence is unnecessary for now)
- A documented "server-state / cache" category: the docs define four client-state categories only, so
  TanStack Query is encapsulated behind `state/query.ts` as an implementation choice (documentation gap)
- The real authentication token flow (ES-019 integration)

Reason:
ES-027 establishes the four-category state architecture: the server-state boundary (TanStack Query behind the
`state/query.ts` thin layer — client, keys, query builders, invalidate helpers), the app-level Session State
store (theme) and the formalized Derived-State selectors, while the Investigation Context (workspace-owned)
and View State (region-local) keep their existing owners. Mutations, richer preferences, View State
persistence and the auth flow belong to later specifications.

---

## ES-028

- A dedicated **AI Runtime container**: the AI Runtime is an in-process backend layer (`app/ai/`), not a
  standalone server, so it is co-located in the backend image; a separate deployment unit is deferred until it
  becomes independently deployable
- The **data tier is unused at runtime**: the backend services are unbound (503) with no repository adapters
  (ES-004+ TD), so the `data`-profile stores run but nothing connects to them yet; the containerized frontend
  therefore shows error states (auth-gated 401/403 + unbound 503, no MSW in the prod build) until data wiring
  lands
- **Image build/run not exercised in-session**: `docker compose config` validated both the default and the
  `data` profile, but Docker Desktop's daemon could not be started non-interactively, so `docker compose
  build`/`up` must be run on the user's Docker
- Production hardening deferred: image vulnerability scanning, resource limits, non-dev nginx tuning,
  TLS/edge termination, a published/versioned image pipeline (CI build & push), and staging/production compose
  overlays
- Reverse-proxy base-URL coupling: `VITE_API_BASE_URL` is baked to `http://localhost:8080` at build time, so a
  different published host/port needs a rebuild (a relative-base option is a future refinement)

Reason:
ES-028 delivers the containerization of the existing deployment units — multi-stage wheel-based backend image,
nginx-served frontend image with a same-origin reverse proxy, and a root compose with an opt-in `data`
profile — without touching application code. The standalone AI Runtime, live data wiring, image build
verification and production hardening belong to later specifications.

---

## ES-029

- Env-scoped operational **parameter overrides** (values that differ per environment beyond validation) are
  not introduced — no concrete consumer exists yet, so adding them would be speculative; the Environment type
  + validation is the current Environment Configuration surface
- Only `POSTGRES_PASSWORD` / `NEO4J_PASSWORD` are validated (the only secret-bearing settings today); AI
  provider keys (ES-009) are unmodeled and unvalidated, and additional secret-bearing settings must be added
  to `validate_secrets` as they appear
- The insecure-default rule matches a fixed placeholder set (`change_me`); a broader "was this explicitly
  provided vs defaulted?" check and richer per-setting validation are deferred
- Frontend configuration validation: `communication/config.ts` (Presentation Deployment Configuration) is
  currently untyped/unvalidated beyond a base-URL fallback; formalization is deferred until it grows
- Configuration retirement/traceability tooling (configuration-management §8) beyond code-level ownership
  documentation is out of scope

Reason:
ES-029 adds the missing Environment Configuration type (typed `Environment`) and the Configuration Validation
lifecycle stage (startup fail-fast rejecting insecure secret defaults outside development), leaving Platform
(settings.py) and Domain (database.py) configuration unchanged. Env-scoped overrides, broader secret coverage
and frontend config validation belong to later specifications.

---

## ES-030

- No **registry publish** and no **actual environment deployment / CD promotion**: CI builds the images for
  validation only, because no registry or environment target is defined yet — publishing/deploying would invent
  infrastructure
- Image **scanning / signing / SBOM** and provenance are not part of the pipeline
- **Secrets delivery** for production (real POSTGRES/NEO4J passwords, AI keys) is operator-supplied via `.env`;
  no secret-management integration for deployment
- The `docker-compose.prod.yml` overlay demonstrates the dev→prod deployment shape but the app cannot serve
  real production data yet (services unbound); it is not a hardened production configuration (no TLS/edge
  termination, resource limits, or log/observability wiring)
- Deployment/release **scripts** (`scripts/` is still an empty `.gitkeep`) and environment promotion tooling
  are deferred
- CI does not yet cache the backend pip install or run path-filtered/matrixed jobs (kept simple)

Reason:
ES-030 delivers the concrete deployment/release automation the technology-independent Deployment and Release
Management docs leave open: a GitHub Actions CI that validates each deployment unit and builds the deployment
artifacts, plus a production compose overlay for the Operational stage. Registry publish, real environment
delivery, image supply-chain security and production hardening belong to later specifications (no target exists
yet). This ES also applied five curated architectural documentation clarifications (see Documentation
Improvements Already Applied).

---

## ES-031

- A full **metrics stack** (Prometheus scraper, Grafana, histograms/quantiles, per-endpoint labels) — only a
  minimal hand-rolled `/metrics` (counters + duration sum/count + uptime) exists; no scraper is deployed
- **Dependency-probing readiness**: `/health/ready` reflects startup completion only (the backend runs without
  live databases); a readiness that probes the persistence adapters belongs to when those are live (ES-004+ TD)
- **Log shipping / retention / aggregation** and a structured-log schema contract are out of scope (the JSON
  logs are emitted to stdout only)
- **Distributed tracing** (spans, trace propagation across deployment units) beyond request/correlation-id
  threading is deferred
- **Frontend / client observability** (client error/telemetry reporting beyond the ErrorBoundary) is out of
  scope — backend operational focus
- Metric cardinality is unbounded in principle (method+status keys are low-cardinality today, but no bound is
  enforced)

Reason:
ES-031 delivers operational Platform Observability: a correlation contextvar threading request/correlation ids
through every log, config-selectable structured (JSON) logging validated fail-fast via ES-029, a minimal
dependency-free `/metrics` surface and a readiness probe distinct from liveness — leaving the ES-021 audit
trail untouched. A full metrics/tracing stack, dependency-probing readiness, log shipping and frontend
observability belong to later specifications.

---

## ES-032

- The shared support scaffolds only the **Investigation family** doubles/builders; Graph/Memory/Planner doubles
  are added to `tests/support` when ES-034 (Integration) reuses them (avoids speculative unused code)
- Existing tests still **duplicate** their in-memory doubles — they are intentionally not migrated to the shared
  support (respecting "do not redesign completed work"); migration can happen incrementally
- Coverage is **measured/reported only** — no threshold/gate, no coverage baseline artifact comparison, no
  Codecov-style consumer wired up (consistent with the doc's "not implementation quality metrics")
- The `architecture` / `integration` / `operational` markers are **registered but not yet applied** to existing
  tests — ES-033/034 categorize the relevant suites; today's tests are implicitly Domain Validation
- Frontend test taxonomy is directory/naming-based (Vitest has no marker system) rather than an explicit taxonomy
- No mutation / property-based / contract testing

Reason:
ES-032 establishes the Test Foundation the specialized validation specs build on: the validation taxonomy
(pytest markers + `--strict-markers`), a shared `tests/support` doubles/builders scaffold proven by a foundation
test, coverage visibility (measured/reported, no gate) in both suites and CI, and `TESTING.md`. The mature
existing suites are left unchanged; broader double consolidation, marker application and richer testing
techniques belong to ES-033/ES-034 and later specifications.

---

## ES-033

- The import scanner assumes **absolute imports** (verified true today); it does not resolve relative imports —
  if relative imports are ever introduced the scanner must be extended
- Boundary coverage is the **enforceable core** (domain/application/AI/presentation/shared import rules + the
  no-uuid/no-clock constraint); finer Ownership/Interaction constraints (e.g. "no service accesses another
  service's persistence", per-service repository ownership) are not yet asserted
- No-generic-CRUD / no-service-locator constraints are documented decisions but **not machine-verified** here
- The clock check targets `datetime.now`/`utcnow` calls specifically; other clock sources (e.g. `time.time`)
  are not asserted in domain/application (none exist today)
- Frontend architecture validation asserts only the single-`fetch`-boundary rule; deeper frontend layer rules
  (e.g. layered import direction pages→sections→components→ui) are not yet enforced

Reason:
ES-033 delivers Architecture Tests as static import-boundary checks (marked `architecture`) that verify the
Clean Architecture layering and the no-uuid/no-clock Permanent Engineering Decisions, plus one frontend
single-boundary rule (`fetch` only in the communication layer). Broader ownership/interaction constraints and
deeper frontend layering rules belong to later specifications.

---

## ES-034

- Live-infrastructure integration (real PostgreSQL/Neo4j/Qdrant/Redis-backed integration tests) —
  the persistence adapters themselves are still deferred (ES-004+ TD), so integration validation
  runs over the shared in-memory doubles; live-database integration tests belong to the adapter
  implementations
- Existing suites are still **not migrated** to the shared support (ES-032 decision preserved);
  only the new integration suite consumes it
- Security-chain (authn→authz→audit) cross-domain flows are not re-verified in the integration
  suite — the ES-019/020/021 presentation tests already exercise the real chain end to end;
  duplicating them under the `integration` marker was avoided deliberately
- The Memory Agent ↔ RAG pipeline **production orchestrator** (a top-level composer that runs the
  agent then the pipeline) remains deferred (ES-013 TD) — ES-034 verifies the collaboration in
  tests without introducing the orchestrator
- Frontend↔backend cross-deployment-unit integration (a browser/API contract test) is out of
  scope — the frontend already validates its communication layer against the mirrored envelope
  types; a real cross-process contract test needs a running backend target

Reason:
ES-034 delivers Integration Validation as in-process cross-domain collaboration tests over the
architectural seams that exist today. Live-infrastructure integration follows the deferred
persistence adapters; deliberate non-duplication keeps the suite focused on collaborations not
already verified elsewhere.

---

## ES-035

- **Live-model behavioral evaluation** (real LLM/embedding providers, evaluation datasets, model
  benchmarks) — explicitly out of the doc's scope (ai-validation §3) and no concrete provider exists
  (ES-009 TD); behavioral validation runs over deterministic scripted provider doubles
- The behavioral matrix is **hand-curated** (`ADVERSARIAL_RESPONSES`), not property-based/fuzzing —
  a property-based testing library would be a new dependency the testing docs do not call for
- **Decision-quality validation** (is the selected action/strategy a *good* choice for the state?) is
  not verifiable without a real reasoning provider — only architectural behavior (typed contract, safe
  degradation, consistency, provenance) is validated
- Frontend AI-facing validation is out of scope (no AI surface exists in the frontend)

Reason:
ES-035 delivers AI Validation as behavioral validation of the architectural AI contracts that exist
today, over deterministic fakes. Model-quality evaluation belongs to when concrete providers exist;
richer testing techniques remain future work consistent with ES-032.

---

## ES-036

- **Load / stress / soak testing and latency benchmarking** (thresholds, percentiles, load-generation
  tools) — explicitly outside the doc's scope (performance-reliability §3: no benchmarking tools, no
  implementation performance metrics); validation asserts behavioral consistency, not speed
- **Live-infrastructure resilience** (database outage/recovery, connection-pool exhaustion, container
  restart drills) — the persistence adapters are still deferred (ES-004+ TD); infrastructure-level
  resilience follows them and the deployment hardening deferred in ES-028/030
- Scalability is validated as **concurrency safety at small scale** (50 concurrent service operations,
  8-thread metric contention) — horizontal scaling / multi-instance behavior has no target environment
- Frontend operational validation (client-side reliability/telemetry) remains out of scope (ES-031
  decision: backend operational focus)

Reason:
ES-036 delivers Performance & Reliability as architectural operational assurance over the surfaces
that exist today. Benchmarking is documented as out of scope; infrastructure-level resilience and
scale-out validation belong to the deferred persistence/deployment work.

---

## ES-037

- Concrete `StateAssembler` implementation (the Investigation Workspace / Context Builder that
  assembles the next Investigation State) — the loop consumes the port; assembly remains deferred
  (carries the ES-011 TD forward)
- DI / lifecycle wiring of the Investigation Loop and Retrieval Flow (no runtime invocation surface
  yet); the decision on the public exposure of `POST /api/v1/planner/actions` is explicitly open
  (ADR-010 Notes, audit plan Phase 2)
- Generic AgentRuntime/AgentResult bridge for the typed agents (carries the ES-011/012 TD forward)
- Decision Engine and the specialized agents (carries the ES-010 TD forward)
- Loop policy depth: cycle budget is the only termination policy; confidence-threshold completion,
  no-op/delay decisions and richer replanning policies are deferred until documented

Reason:
ES-037 closes the composition gap (audit finding B2/B4, ADR-010): the AI Runtime now owns the
Investigation Loop (Planner Agent → Planner Service, one action per cycle, observed state, bounded
budget) and the Retrieval Flow (Memory Agent → RAG Pipeline). Composition exists and is tested over
in-memory doubles; the concrete state assembler, live wiring and richer loop policy belong to later
specifications.

---

## ES-039

- Outbox table/collection schema, projector scheduling and the concrete embedding adapter (follow the
  persistence adapters; ADR-012)
- Concrete external-knowledge providers and the Retriever's external-strategy execution over the new
  port (API keys / integrations deferred by scope)
- Concrete provider timeouts and circuit breakers (belong to the concrete LLM/embedding/external
  adapters; ADR-013)
- Content-addressed object store for evidence payloads (enters via ADR-011 category path with its own
  decision; database-architecture §8b)
- Erasure implementation (tombstoning / crypto-shredding per store; follows adapters;
  data-lifecycle.md)
- Frontend type/mock derivation tooling from `docs/api/openapi.json` (artifact + freshness check exist;
  derivation is implementation work)
- API exposure of Outcome and Trace operations (service contracts exist; presentation surface follows
  the Decision Engine / workspace needs)
- Concrete operation-context type and scoping-policy implementation (authentication-authorization
  §6a/§6b; introduced with the concrete authorization policy, ES-020 TD)
- AC-14 mechanical enforcement (becomes checkable once adapters exist)

Reason:
ES-039 closes the architecture gap analysis (`ARCHITECTURE-GAPS-2026-07-03.md`): every finding is
resolved at the decision/contract level with in-memory-verified code where no live infrastructure is
required. Everything requiring live databases, provider keys or deployment targets stays deferred by
the task's explicit scope ("persistence & AI runtime integrations later").

---

## ES-040

- **Autogenerate workflow not yet exercised**: the baseline migration is hand-written (mirroring the
  ORM metadata and its naming convention); future schema changes may use `alembic revision
  --autogenerate`, which the deterministic naming convention was set up for
- **No pagination/streaming on the list queries** — adapters return full tuples, mirroring the API
  pagination TD (ES-015+); introduced together when pagination lands
- **Connection-pool tuning and retry policy** not configured (engine defaults + `pool_pre_ping` only);
  operational hardening follows deployment needs
- **Erasure/retention (data-lifecycle.md)** not implemented — deliberately unblocked by the schema
  (plain rows, no cascading semantics that would prevent tombstoning/erasure later; slice plan §4)
- **In-session live verification not possible**: Docker Desktop's daemon could not be started
  non-interactively on this machine (same constraint ES-028 recorded), so the live suite ran neither
  here nor against a local store; it is executed by the CI `backend-live` job and locally via
  `docker compose --profile data up -d postgres` + `POSTGRES_HOST=localhost pytest -m live`

Reason:
ES-040 delivers the PostgreSQL persistence vertical for the Investigation family: the Alembic
baseline, the ORM models/mappers, the six repository adapters and the opt-in live validation strip.
Operational hardening, pagination and lifecycle tooling belong to later specifications.

---

## ES-041

- **Embedding provider port usage, semantic retrieval and Qdrant synchronization** remain deferred
  (ADR-012 outbox — second vertical slice, as the slice plan §3 prescribes)
- **No queries beyond the frozen port** (no list-by-type/status, no metadata retrieval — the ES-007
  domain-field TD stands unchanged)

Reason:
ES-041 delivers exactly the versioned MemoryItem adapter over the ES-040 foundation. Everything
embedding/semantic belongs to the second slice (ADR-012).

---

## ES-042

- **Graph store remains explicitly unavailable**: the Neo4j adapter (ES-006 TD) is out of the slice;
  the Planner composition uses the explicit-contract unavailable repository
  (`graph.store_unavailable` → contained failed result) and the Graph API endpoints keep their 503
- **Redis is not bound** — no consumer exists (ADR-011 demand-driven integration)
- **The transitional `POST /api/v1/planner/actions` surface is unchanged** — its fate (default:
  removal) is decided in ES-044 (slice plan §5 V-2)
- **No DB-outage retry/backoff or circuit breaker**: connectivity failures are translated to the
  stable 503 `api.persistence_unavailable`; resilience mechanics are a concrete-adapter concern
  (ADR-013, ES-043+ and the hardening slice)
- **Readiness probes PostgreSQL only** — the unbound stores (Neo4j/Qdrant/Redis) are deliberately not
  probed (readiness reflects what business traffic actually requires)
- **Commit-at-teardown**: the request transaction commits in the dependency teardown after the
  endpoint returns (FastAPI ≥0.106 runs it before the response is sent, so a commit failure still
  translates through the standard error envelope); no explicit early-commit surface exists yet

Reason:
ES-042 turns the backend from a skeleton into a live system for the slice's stores: the
investigation/memory/planner services are bound to the concrete adapters with request-scoped
transactions, failure contracts are explicit and stable, and readiness reflects the bound store.
Graph/Redis binding and resilience hardening belong to later specifications.

---

## ES-043

- **No startup fail-fast for the AI key**: the provider is constructed per request (run seam), not
  at startup, and `GOOGLE_API_KEY` is SecretProvider-owned (K-1), not a settings field — so ES-029's
  `validate_secrets` is untouched. A missing key surfaces as the explicit `secret.not_found` (503)
  at composition. Startup-time validation in production-like environments follows when the provider
  becomes a startup-constructed component
- **Circuit breaker deliberately absent** (ADR-013 §4: concrete-adapter hardening; slice plan §4 —
  timeout + total error mapping are the slice's mandatory protections) and **no retry/backoff**
  (single bounded call per generate)
- Richer LLM contract shapes (messages/roles, streaming, structured output, batch) remain deferred
  (ES-009 TD); the adapter maps prompt→text over one REST endpoint
- **Live smoke not yet green**: the `GOOGLE_API_KEY` line in the root `.env` is empty (the value was
  not actually saved), so the smoke and the valid-key live run skip; the invalid-credential path is
  live-proven instead (see ES-044). To be run when the key is supplied

Reason:
ES-043 delivers the first concrete LLM provider (Gemini over httpx): bounded execution, total error
mapping and key hygiene as the port contract demands. Hardening (breaker/retry) and richer contract
shapes belong to later specifications.

---

## ES-044

- **Objectives source** is a design decision of this ES: a single objective derived from the
  investigation title; richer objective management awaits documentation
- **State confidence** = the strongest finding's confidence (0.0 with no findings) — an assembly
  decision to revisit with the Decision Engine; task fields stay empty (no Task service — the
  "Task service ownership" documentation gap stands)
- **Run surface is synchronous** with a small configurable cycle budget (V-1 confirmed; an
  async/job model is a state-ownership question that would trip the ADR-014 threshold)
- Loop policy depth unchanged (cycle budget as the only termination policy — ES-037 TD stands)
- `InvalidActionError` stays reachable through the run seam (an agent-emitted `depth=0` would raise
  it out of the executor as a documented precondition violation → 422); the 422 mapping is retained
- The full valid-key live run (real Gemini deciding over the live stack) awaits the key (see
  ES-043 TD); the loop's live behavior is otherwise proven by the invalid-credential run

Reason:
ES-044 wires the Investigation Loop at runtime (concrete StateAssembler + DI composition + the
investigation-level run surface) and removes the transitional planner-actions resource (V-2
confirmed). Objective/tasking depth and richer loop policy belong to later specifications.

---

## ES-045

- **Read-only surfaces**: outcome creation stays a service-internal operation until the Decision
  Engine arrives; the trace is written only by the platform (loop / recorded steps)
- No pagination on the trace listing (mirrors the platform-wide list-pagination TD)

Reason:
ES-045 exposes the persisted Trace and Outcome through thin read controllers, closing the ES-039
"API exposure of Outcome and Trace" deferral. Write surfaces and pagination belong to later
specifications.

---

## ES-046

- **Dev-grade identity model**: the shared-token authenticator's subject is caller-declared
  (possession of `DEV_AUTH_TOKEN` gates entry) — per-subject credentials, token continuity/refresh
  and `WWW-Authenticate` semantics belong to the production identity provider (second phase, V-3)
- **Owner==subject is not enforced on create**: any authenticated identity may create an
  investigation with any owner value (§6a defines creation loosely); tightening it is a policy
  refinement for the production IdP phase
- **Policy path vocabulary is closed**: an operation the policy does not recognize is denied, so a
  future resource surface stays 403 until the policy learns it (deliberate least-privilege bias)
- **Two sessions per request** on owner-scoped operations: the authorizer reads ownership over its
  own request-scoped session before the endpoint's service session opens (read-only; acceptable at
  dev scale — collapsing to one shared session dependency is a later refinement)
- `DEV_AUTH_TOKEN` is SecretProvider-owned (like `GOOGLE_API_KEY`) and therefore outside ES-029's
  settings-based `validate_secrets` (same stance recorded in ES-043 TD)

Reason:
ES-046 delivers the slice's real security chain: shared-token authentication over the
SecretProvider, the §6b operation context carried explicitly into the decision, and the first
concrete authorization policy (owner scoping, §6a) replacing deny-all at runtime. The production
identity provider and policy depth belong to later specifications.

---

## ES-047

- **Dev token UX is minimal**: one header field storing `subject:token` (localStorage with an
  in-memory mirror); no logout/expiry, no masking beyond not re-displaying — replaced with the real
  authentication flow alongside the production IdP
- **DTOs are hand-written transitional copies** (api-design §14a) — type/mock derivation tooling
  from `docs/api/openapi.json` remains deferred
- **MSW is fully removed** (dev flow hits the real backend; the page tests already mocked loaders
  directly and only the sample data module remains as test fixtures) — a browser mocking layer can
  return if a demo-without-backend mode is ever wanted
- **Create/attach forms are deliberately minimal** (title+priority; source+content with a fixed
  `unverified` integrity) — richer evidence ingestion is the documented future capability
  (database-architecture §8b)
- The platform-level investigation list is still deferred (no list endpoint), so the landing page
  creates-and-navigates; returning to an old investigation needs its URL

Reason:
ES-047 closes the first vertical slice: the browser flow (create → evidence → run → trace) runs
against the live backend with no mocks, escalated/exhausted outcomes are presented, and the
Delivery Record now declares the slice operational (roadmap §7 gate satisfied). Production
authentication UX, derived DTO tooling and richer ingestion belong to later specifications.

---

## ES-048 (second slice, Part 1)

- **Relationship-type vocabulary deferred** (graph-service §11a) — the three deferral conditions were
  confirmed at implementation: types stay open string value-objects; a relationship is a single Neo4j
  type ``REL`` with the domain type as a **property** (never embedded in constraints); the schema
  version marker is **generic** (tracks any migration). So adding the vocabulary later is a
  Graph-Service write-validation step + versioned migration step — it does not reopen the migration
  mechanism. Semantic-equivalent-duplicate rejection and type deprecation belong to that later step.
- **Graph analytics / ThreatGraph out of scope** (ADR-007 stays deferred): only the base
  Entity/Relationship model + single-source neighbourhood traversal. Attack-path/shortest-path/typed
  traversal are not implemented.
- **Relationship uniqueness is not DB-enforced**: Neo4j Community-edition relationship uniqueness
  constraints are avoided; a property **index** on ``r.id`` backs lookups, and the application supplies
  unique relationship ids (API-generated). Node uniqueness (``Entity.id``) is constraint-enforced.
- **Schema bootstrap is not run in the app lifespan** (startup must not require a live graph store);
  it is invoked by the live-test setup and will be invoked by the ES-053 seed utility.
- **Readiness gates on PostgreSQL only** (deviation from the plan's "Neo4j down → not_ready" exit
  criterion — flagged): readiness now **probes and reports** Neo4j truthfully (`neo4j: ok|unavailable|
  not_initialized`) but does not gate overall-ready on it, because graph operations degrade to
  contained failures by design (planner-service §8) and because CI's `backend-live` lane provides
  PostgreSQL only. Gating the whole platform on a graph blip would contradict the failure-isolation
  philosophy.
- **Managed-transaction retry only** (no explicit connection-pool/backoff tuning beyond driver
  defaults); circuit-breaker/hardening is Milestone G.

Reason:
ES-048 makes Neo4j the real authoritative graph store: the versioned idempotent migration mechanism,
the concrete adapter (real ``find_neighbors``), and the runtime binding that takes the Graph API and
the planner's graph action live. Vocabulary discipline, graph analytics and hardening belong to later
specifications.

---

## ES-049 (second slice, Part 2 foundation)

- **No request-path wiring yet**: this ES delivers the port + adapters only; the first consumers are
  the ES-050 outbox projector (memory port) and the ES-051 semantic retriever (AI port). No DI /
  lifespan / readiness / OpenAPI change (purely additive).
- **Single-text embedding** (batch deferred; ES-009 TD stands) — the projector embeds one Memory
  Item at a time.
- **No circuit breaker / retry / backoff** (ADR-013 §4, Milestone G): the mandatory protections are
  the bounded timeout + total error mapping (both present). Free-tier Gemini rate-limits surface as
  `EmbeddingProviderError` (observed transiently when many live calls run back-to-back) — no backoff.
- **Embedding dimension not pinned/validated** here — the Qdrant collection's vector size and its
  consistency with the model's output dimension is ES-050's collection-bootstrap concern.
- **Embedding model id is configuration** (`GEMINI_EMBEDDING_MODEL`, default `gemini-embedding-001`);
  the provider decision (Gemini, K-2) is fixed, the concrete model/dimension is adjustable.

Reason:
ES-049 realizes ADR-012 §3's application-owned embedding port and the concrete Gemini embedding
adapter (K-2), setting up ES-050 (outbox → embedding → Qdrant) and ES-051 (semantic query embedding)
on one shared provider. Batch embedding, resilience hardening and dimension pinning belong to later
specifications.

---

## ES-050 (second slice, Part 2 core)

- **`MemoryItem.content` added (Option B, owner decision)**: the docs describe Semantic Memory as
  text (summaries/notes) but the implemented model had no free-text field. Added additively
  (default `""`) across domain/Postgres/API so the frozen memory surface is extended, not reopened.
  Full authoring UX (rich content, versioned regeneration) is out of scope.
- **Outbox write is in the Postgres memory adapter's `add`** (same transaction as the memory row),
  not the Memory Service — the widely-constructed service constructor stays unchanged (churn/risk
  minimized). The projector (the logic) is Memory-Service-layer-owned; only the transactional write
  lives in the adapter. Deprecation (`update` in place) writes no outbox (embed text unchanged).
- **No embedding regeneration / versioning / GC** (memory-service Embedding Lifecycle): a model
  upgrade or content edit re-embeds via a new version's outbox record, but there is no controlled
  bulk-regeneration or stale-embedding cleanup. Deleting a Memory Item does not delete its Qdrant
  point (no delete path yet). Single-text embedding only (batch deferred).
- **Projector runner is single-process, best-effort** (ADR-012 async projector; no separate worker,
  no dead-letter queue, no backoff schedule beyond the poll interval; a failed record stays `failed`
  and is not auto-retried by the loop — it is observable for a future retry policy). Circuit breaker
  and multi-instance/scale-out are Milestone G.
- **Readiness gates on PostgreSQL only** (consistent with ES-048): Qdrant is probed and reported
  (`qdrant` field) but does not gate — retrieval degrades to contained failure.
- **AC-14 not mechanically enforced** — the implementation is AC-14-compliant by construction (no
  request path writes to two stores; the outbox + memory commit in one Postgres transaction, Qdrant
  is written only by the async projector), but the static/integration check itself is Milestone G.

Reason:
ES-050 delivers ADR-012's core: the transactional outbox (written atomically with the Memory Item),
the idempotent embedding projector (deterministic Qdrant point per item), the Qdrant collection and
the background runner. Regeneration/versioning/GC, resilience hardening and AC-14 enforcement belong
to later specifications.

---

## ES-051 (second slice, Part 3)

- **Retrieval runs once per run** (owner decision): the runner executes the Retrieval Flow before
  the loop and the assembler preserves the attached knowledge across cycles — one Memory Agent
  call + one query embedding per run, not per cycle. Per-cycle (or planner-actioned) retrieval is
  a future refinement that would need a cost/latency decision.
- **Retrieval failure is log-only** (no trace entry on the failure path): `MemoryAgentError` /
  `InsufficientContextError` are contained in the runner and the run proceeds without retrieved
  knowledge. An empty knowledge base fails the pipeline's validation gate by design (the normal
  early-investigation condition), so tracing every failure would spam the journal — revisit with
  the Decision Engine.
- **External strategy contributes nothing** (Milestone C): the composite retriever executes
  semantic/structured/graph; `external` yields no items (never an error). `hybrid` expands to the
  three organizational strategies.
- **Knowledge-line content is bounded (300 chars)** in the planner prompt — context
  compression/budget/ranking remain rag §16 deferrals.
- **Semantic search is cross-investigation by design** (memory is the shared knowledge layer,
  §6a; MemoryItem is "reusable across investigations") — no investigation filter on the vector
  search; provenance carries the source. Deprecated Memory Items are filtered out of retrieval
  (semantic + structured): deprecation marks knowledge no longer valid.
- **`memory.vector_store_unavailable`** added (the Qdrant search maps driver/transport failures
  to it, mirroring `graph.store_unavailable`); the projector's write path keeps its ES-050
  containment unchanged. The new code is contained **per strategy** in the retriever, so a
  vector-store outage silences semantic retrieval only.
- **No re-ranking / no score thresholds**: matches map back to the authoritative Memory Items
  (content never read from the derived store, §8a), cosine scores clamp to Confidence [0,1] and
  are surfaced as-is. Quality evaluation remains out of scope (ES-035 stance).
- Resource bounds are constants (semantic limit 5, graph seeds 3, neighbours 10) — configuration
  surface deferred until a consumer needs to tune them.

---

## ES-052 (second slice, Part 4)

- **Query-parameter listing** (`GET /api/v1/memory?investigation_id=…`): memory stays a
  Memory-Service-owned top-level resource — a sub-resource under `/investigations` would imply
  Investigation Service ownership (AC-07). No pagination (platform-wide list-pagination TD stands).
- **Shared-knowledge read** (§6a): the listing is open to any authenticated identity — no owner
  scoping on memory reads (isolation happens at promotion, not retrieval); the existing
  OwnerScopedAuthorizer's `/api/v1/memory` prefix rule already covers the new operation.
- **All statuses returned** (deprecated included, status visible in the UI) — the service listing
  stays neutral; only *retrieval* (ES-051) filters deprecated knowledge.
- **Memory region is read-only**: no memory authoring UX (create/update/deprecate from the
  workspace) — knowledge promotion flows remain a later capability.
- **Browser-pane caveat** (verification infra): the Claude preview tunnel strips `Authorization`
  headers, so in-pane auth flows 401; verified instead via headless Chrome over CDP against the
  live stack (real browser, no mocks).

---

## ES-053 (second slice, close)

- **Seed is additive and non-destructive**: each run creates a fresh demo investigation (UUID id);
  the ``demo-*`` graph entities are reused by canonical identity (idempotent creation); no
  truncation of user data. Seeding goes through the **services**, never raw persistence.
- **Derived-collection recreation on dimension mismatch**: the live test suites leave
  ``memory_embeddings`` at their fake-embedder dimension (3) on the shared local Qdrant; the seed
  recreates the collection at the configured dimension (768) — legitimate because the derived
  representation is never authoritative (ADR-012). Earlier points are lost (bulk re-projection
  stays an ES-050 deferral); a test-scoped collection name is backlogged.
- **Key-less degrade**: without ``GOOGLE_API_KEY`` the seed leaves outbox records pending (the
  app's background projector embeds them later) — the projector path is never faked.
- **Environment gotcha (recorded for operators)**: PowerShell ``-match`` is case-insensitive and
  the Turkish locale lowercases ``I`` to ``ı``, so ``[A-Z]`` classes silently fail on names like
  ``GOOGLE_API_KEY`` — load ``.env`` lines with ``-cmatch``. (This had masked the env-var path of
  the key; live_ai suites passed via their own ``.env`` fallback.)
- **Demo happy-path caveat (external)**: on the closing day Gemini ``generateContent``
  (gemini-3.5-flash) returned intermittent 503s over several hours, so the browser demo's run
  ends **escalated** with the stable ``ai.llm_provider_error`` — the documented ADR-013 degrade
  path, user-visible. The retrieval-wired happy path (real Memory Agent decision, real query
  embedding, Qdrant search, chronological trace) is live-proven by the ``live_ai`` suite (4/4,
  ES-051 entry); the browser walkthrough re-runs with one command when the provider has capacity.

---

## ES-054

- **Model choice is owner-driven** (MiniMax-M3 on NVIDIA NIM; the Gemini capacity outages were
  the trigger). `NVIDIA_MODEL` is configuration; the provider decision realizes ADR-005's
  replaceable-port claim with a second concrete adapter. **Embedding stays on Gemini** — the
  Qdrant collection's 768-dim vector space is bound to the embedding model (ES-050); switching
  embedders is a separate re-projection decision.
- **`LLM_PROVIDER` selection is composition-time config** (closed enum gemini|nvidia); an invalid
  value fails at composition, not at startup — startup-time validation for provider selection
  follows if the provider ever becomes a startup-constructed component (same stance as the ES-043
  key-validation deferral). No retry/fallback chain between providers (Milestone G hardening).
- **Reasoning normalization is adapter-owned**: M-class models may emit `<think>…</think>` inside
  the answer content; the adapter strips it because `LLMResponse.text` is the answer contract —
  strict-JSON consumers (planner/memory agents) must never parse provider-specific reasoning
  artifacts. Reasoning-only responses map to `LLMProviderError`.
- **Default execution bound 90s** (reasoning models answer slower than flash-class; ADR-013's
  mandatory protections — bound + total error mapping — unchanged). `max_tokens` 8192 leaves room
  for visible reasoning plus the answer.
- **Dev auto sign-in is a dev-server-only convenience**: `VITE_DEV_AUTH_CREDENTIAL` in the
  gitignored `frontend/.env.local`; production builds never receive the variable, the backend
  security chain (ES-046) is untouched, and an explicitly entered credential always wins. The
  vitest runtime force-empties the variable so the developer's real `.env.local` cannot leak into
  tests.
- `live_ai` does not yet cover the NVIDIA adapter (its gating is `GOOGLE_API_KEY`-shaped); the
  real-provider proof is the ES-054 smoke + demo run — a provider-parameterized live lane is
  future work.

---

## ES-055 (Milestone B, part 1)

- **The bridge slot collapsed**: the plan's "generic Agent Runtime bridge" ES was verified already
  closed by ES-039 (typed generic `Agent[RequestT, ProductT]` + `AgentResult`, `AgentRuntime.run`
  as the single host) — Milestone B numbering shifted rather than shipping a filler ES.
- **The engine is not an agent** (agent-architecture §6): it does not run through the Agent
  Runtime; its caller (the loop) contains failures instead. `TraceEntryKind.OUTCOME_SYNTHESIS`
  added additively (kinds are stored as strings — no migration).
- **Skips are silent, failures are traced**: skipped synthesis (outcome exists / no confirmed
  finding) is log-only to avoid trace noise on empty investigations; a failed synthesis leaves an
  OUTCOME_SYNTHESIS entry with the stable code.
- **No re-synthesis path**: a completed investigation re-run keeps its first outcome (0..1);
  outcome revision/regeneration awaits the analyst-review capability (REVIEWED/ACCEPTED statuses
  are modelled but unwritten).

---

## ES-056 (Milestone B, part 2)

- **Validation never mutates findings**: the agent reports issues (the documented four-way
  vocabulary); finding status transitions stay with the analyst and the owning service (human
  oversight). The assessment's consumption is the Decision Engine prompt — deterministic folding
  of issues into outcome fields was deliberately avoided (synthesis owns the folding).
- **Raise-on-malformed is a deliberate contract divergence** from the planner/memory agents: an
  empty assessment is not a neutral fallback (it would read as a clean bill of health), so
  transformation failures raise `ValidationAgentError` and the loop contains them — synthesis
  proceeds without an assessment, traced.
- **All findings are assessed** (not only confirmed ones): flagging PROPOSED findings before an
  analyst confirms them is exactly the trust value the doc describes.
- **Validation runs at completion only** (before synthesis): per-cycle validation would multiply
  provider calls on a synchronous surface; revisit if the run surface goes async.
- `TraceEntryKind.VALIDATION` added additively.

---

## ES-057 (Milestone B, close)

- **ThreatGraph determination (ADR-014 threshold check)**: the Graph Analysis Agent consumes the
  existing Graph Service surface only (get/neighbors/incident relationships, the retriever's
  bounds) — no new traversal semantics, no boundary change ⇒ **below the RFC threshold**; ADR-007
  (ThreatGraph) remains Accepted-and-deferred until attack-path infrastructure (shortest-path,
  multi-hop analytics) is actually built (Milestone-later work, backlog).
- **Enrichment, not planner-selected agent dispatch**: the agent runs once per run in the runner's
  enrichment phase (like retrieval) and its observations join the planner-visible knowledge as
  `[graph-analysis]` lines. The documented "planner selects agents" dispatch model awaits the
  planner action-catalogue ES (deferred since ES-008) — recorded deviation, consistent with the
  ES-051 retrieval-consumption shape.
- **Observation provenance is snapshot-bound**: entity references outside the assembled
  neighbourhood are discarded from an observation's provenance (the observation text survives);
  raise-on-malformed mirrors ES-056 (an empty analysis would read as "nothing notable").
- `TraceEntryKind.GRAPH_ANALYSIS` added additively; the flow records its own trace entry
  (RetrievalFlow pattern) since it runs outside the loop.
- The assembler gained an optional `graph` dependency (additive constructor default `None`;
  graph-less compositions and every pre-existing test remain untouched).

---

## ES-058 (Milestone C, part 1)

- **Concrete external providers are integration decisions, not architecture** (ADR-014 check):
  the `ExternalKnowledgeProvider` port, the EXTERNAL strategy and the origin-preserving item
  shape were all documented (ES-039 / rag §15 / memory §4); choosing the bundled ATT&CK catalog
  and the NVD CVE API as the first adapters mirrors ES-043/054 (concrete providers need no ADR).
- **Bundled ATT&CK catalog is curated reference data, not a feed**: a revisioned subset
  (~21 techniques, keyword-matched) packaged with the app (hatchling wheel includes it —
  verified) so the baseline external source is deterministic, offline and CI-able; the live
  NVD adapter complements it. Refreshing/expanding the catalog is a data update, not code.
- **NVD key is optional by the provider's own contract** (keyless = harder rate limit):
  deliberate, documented deviation from the LLM adapters' mandatory-key stance — composition
  never fails on a missing `NVD_API_KEY`; the key travels only as the `apiKey` header.
- **Confidence semantics for external items are heuristic by design**: ATT&CK reports a bounded
  relevance heuristic from keyword hits (0.4 + 0.1/hit, ceiling 0.9); NVD reports a fixed
  neutral 0.5 (the API has no relevance measure). External knowledge stays indicative context,
  never organizational fact (§17) — provenance (`source`/`reference`) preserved end to end.
- **Per-provider containment inside the EXTERNAL strategy**: one feed's outage never blanks the
  other (retriever logs the stable code and continues) — finer than the ES-051 per-strategy
  containment, same stance.
- TD: prose objectives rarely hit NVD `keywordSearch` (all-terms match) — the Threat
  Intelligence Agent (ES-059) will issue focused queries (entity names, explicit CVE ids);
  no retry/backoff on external calls (Milestone G family); catalog refresh cadence unowned.

---

## ES-060 (Milestone D, part 1)

- **First exercised RFC (ADR-014)**: the payload store extends ADR-003's ownership map (a
  storage technology owning raw evidence payload bytes) — threshold (a), so RFC-001 precedes
  ADR-015. Both are recorded as Accepted under the ADR-014 §3 self-review provision; the
  owner ratifies by committing (they are ordinary working-tree files until then).
- **Category determination**: the payload store is **primary** storage (payload bytes are not
  reproducible from any other store), not ADR-011 supporting persistence — a "never
  authoritative" store cannot own payloads. Exactly one artifact kind is owned; every other
  ADR-003 assignment is untouched.
- **The integrity value IS the content address** (§8b rule 1) — no domain change: `Evidence`
  keeps its shape; `EvidenceIntegrity` stays an opaque value object; only values with the
  `sha256:` prefix participate in payload semantics, so the inline-content interim (seed's
  "verified", analyst free-text) keeps its exact prior behavior.
- **Address scheme is application-owned** (`payload_address` = `sha256:<64 lowercase hex>`):
  a deterministic derivation from content, not id generation — adapters never mint anything
  (caller-supplies-identifiers discipline intact). Strict address validation in the adapter
  doubles as the path-traversal guard (hostile addresses resolve nowhere, tested).
- **AC-14 shape**: upload (object store write) and attach (PostgreSQL write) are separate
  single-store operations; attach-time payload-existence validation is a read. Content
  addressing makes upload idempotent/retry-safe; orphaned payloads accepted until
  Milestone F (data end-of-life owns deletion/erasure).
- **Boundary interpretation recorded in RFC-001**: payload storage *access* (bytes up/down,
  Investigation-Service-mediated per §8b rule 3) is in scope; format parsing / log
  normalization remain the deferred "evidence ingestion" capability (would need its own
  decision, possibly a distinct service per ADR-004).
- TD: filesystem adapter is single-node dev-grade (S3-compatible adapter → Milestone G);
  upload buffers in memory under `EVIDENCE_PAYLOAD_MAX_BYTES` (streaming upload revisited
  with the async-run RFC family); no payload deletion path (Milestone F); frontend surface
  is ES-061.

---

## ES-059 (Milestone C, close)

- **The flow owns retrieval, the agent owns correlation**: agent-architecture §6 permits the
  Threat Intelligence Agent its external sources, but the typed agent stays a pure
  LLM transformation (ES-056/057 pattern) — the Threat Intel Flow performs the lookups
  through the ES-058 `ExternalKnowledgeProvider` port and hands the retrieved items into the
  context. The agent can therefore never present intelligence the platform did not retrieve
  (references outside the snapshot are discarded from provenance, observation preserved).
- **Focused queries close the ES-058 TD**: the flow queries with the objectives *and* each
  finding-named entity's display name (bounded 5) — entity names are what CVE/IOC lookups
  actually match; results dedupe by (source, reference) and cap at 10 items (prompt budget).
- **Enrichment, not planner dispatch** (the ES-057 stance): once per run, after graph
  analysis, before the loop; observations join the planner-visible knowledge as
  `[threat-intel]` lines; a failed correlation is contained (run proceeds unenriched).
- `TraceEntryKind.THREAT_INTEL` added additively; the flow records its own trace entry.
  The workspace needs no code change for visibility — the trace region renders kinds
  generically (pinned by a new frontend test).
- **Observation vocabulary** = the documented responsibilities verbatim: ioc_enrichment,
  cve_correlation, attack_mapping, threat_actor (closed enum; unknown kinds ignored).
- TD: the run sequence now carries six sequential LLM calls — the NVIDIA 90s default bound
  proved tight for the reasoning model (first live attempt timed out; contained exactly as
  designed, and the demo ran with `NVIDIA_TIMEOUT_SECONDS=180`). Widening the default or a
  compact TI prompt is a Milestone G (resilience) consideration. Per-run intel caching and
  richer IOC extraction (beyond entity names) stay backlog.

---

## ES-062 (Milestone E, part 1)

- **Production authenticator is a new adapter behind the existing port** (ADR-014 check —
  **below the threshold**): the `Authenticator` port (§5, ES-019) already made identity
  technology-neutral, so choosing JWT is an implementation selection like NVIDIA/Gemini behind
  the LLM port — no RFC. `AUTH_PROVIDER=dev|jwt` mirrors `LLM_PROVIDER`; the JWT provider is
  opt-in, `dev` stays the default so every existing flow/test is untouched at rest.
- **Verifier, not issuer** (§4 External Identities): the platform verifies signed tokens; a
  real IdP issues them. Issuance lives only in a dev utility (`scripts/mint_dev_jwt.py`) +
  `tests/support/jwt.py` — never in `app`, so the running platform grows no issuance surface.
  Recorded so the boundary is not eroded later.
- **HS256-only is a security decision, not a limitation**: fixing the algorithm closes the
  `alg:none` and RS/HS confusion downgrade attacks (a token naming any other `alg` is rejected
  before the signature is checked). Hand-rolled over stdlib (`hmac`/`hashlib`/`base64`/`json`,
  the no-vendor-SDK discipline); constant-time signature compare; `exp` **required** (an
  identity must carry a validity horizon, §5 Continuity), `nbf`/`iss`/`aud` enforced when
  present/configured; secret via SecretProvider (`AUTH_JWT_SECRET`), never logged. Asymmetric
  (RS256/JWKS) and refresh-token rotation stay deferred (documented) — HS256 with a shared
  verification secret is the demonstrable self-contained realization.
- **owner==subject on create** (§6a / the ES-047 TD closed): the create endpoint derives the
  owner from the **authenticated subject** (`Depends(require_identity)`), not the request body —
  a client can no longer mint an investigation owned by someone else. `owner` was **removed**
  from `InvestigationCreateRequest` (openapi regen, AC-15) and from the frontend create input
  (the HomePage form no longer supplies it; the credential gate stays). The real-auth-chain
  tests were already authenticating as the subject they set as owner, so they held; the
  auth-bypassing presentation/integration tests gained a shared `override_identity` seam
  (`tests/support/auth.py`) since the endpoint now needs a verified identity.
- **WWW-Authenticate challenge** (the deferred §5 semantics): every 401 now carries
  `WWW-Authenticate: Bearer`, set centrally in the exception handler where errors become HTTP
  (RFC 7235 §3.1) — applies to both authenticators.
- **Two release-gate items closed**: "production IdP replaces dev-grade auth" and "owner==subject
  on create" (release checklist). Dev-grade shared token remains as the `dev` provider.
- **Tests (+22)**: 17 JWT authenticator unit tests (valid→identity, kind mapping, expired/nbf/
  bad-sig/alg:none/RS256/missing-sub/missing-exp/malformed/missing-secret rejections, iss/aud
  enforcement, leeway, secret hygiene), 5 JWT e2e chain tests (no-token 401+challenge, expired
  401+challenge, owner==subject create, foreign 403, system identity), 3 `AUTH_PROVIDER`
  selection tests, 1 owner-from-subject presentation test. Live proof (host backend,
  `AUTH_PROVIDER=jwt`, real stack, tokens minted via the utility): no token → 401
  `WWW-Authenticate: Bearer`; alice creates (no body owner) → 201 owner=alice; alice reads →
  200; bob → 403 `authorization.denied`; expired → 401 + challenge.
- Verification: `ruff` clean; `mypy app` strict clean (180 files); backend default **519
  passed** / 22 deselected; frontend 4-gate green (**74 tests**); `openapi.json` regenerated
  (create request lost `owner`). TD: HS256/shared-secret (asymmetric/JWKS + refresh rotation →
  later); the two-sessions-per-request owner-scope refactor still stands (ES-046 TD); tenant
  scoping is ES-063.

---

## ES-063 (Milestone E, close)

- **Second exercised RFC (ADR-014 threshold c)**: adding a tenant scope changes domain-model
  ownership/scoping semantics, so RFC-002 precedes ADR-016 (like RFC-001/ADR-015 for the payload
  store). Both Accepted under the ADR-014 §3 self-review; §6a gained a realization note; the ADR
  index lists 016. ADR-016 amends ADR-003 (the Investigation gains a scope attribute) with
  ADR-003's text preserved (the ADR-011/015 precedent).
- **Tenant is an added conjunct, never a relaxation**: the policy permits an investigation-scoped
  op only when `identity.tenant == investigation.tenant` **and** the owner rule holds. This
  strengthens isolation (cross-tenant → 403 before the owner check) without broadening any
  existing access — the existing owner-only tests still pass unchanged (all at the default tenant).
- **§6a "a scope expressed as an attribute of the investigation, evaluated by the policy"**
  realized literally: `Investigation.tenant: TenantId` (a typed scope key, caller-supplied from
  the identity — not generated, not inferred from data). No new propagation path: the tenant
  rides the existing operation-context mechanism (§6b) — identity → `OperationContext` →
  `AuthorizationRequest` → policy, all additive (defaults to `DEFAULT_TENANT`).
- **Single default tenant keeps everything backward-compatible**: `DEFAULT_TENANT = "default"`
  lives in the application authorization layer (both the policy and the presentation
  authenticators reference it, dependencies inward). The dev authenticator and claim-less JWTs
  use it; the JWT `tenant` claim overrides it. The migration (0004) adds the column NOT NULL
  `server_default='default'`, backfilling existing rows — so the seed and all prior data stay
  reachable by the default-tenant dev identity.
- **Tenant + owner both derived from the identity on create** (extends ES-062): a client can
  neither own nor place an investigation in a foreign tenant. `InvestigationResponse` exposes
  `tenant` (read-only); the create request does not take it (openapi regen).
- **Scope boundary recorded (RFC-002)**: the shared knowledge layers (Memory, Graph) stay open
  to authenticated identities — a **per-tenant** organizational-knowledge model (promotion/
  retrieval scoped to one org) is a documented follow-up, not decided here. Tenant lifecycle /
  membership / moving investigations between tenants are out (the tenant is an opaque IdP-owned
  scope label, not a managed entity).
- **Tests (+6)**: 3 policy tests (foreign-tenant denied even for the owner, matching tenant+owner
  permitted, `for_context` carries tenant), 1 JWT tenant-claim test + 1 default-tenant test, 1
  e2e cross-tenant isolation test (alice@acme creates → alice@other 403 → alice@acme 200); the
  frontend surfaces tenant in the workspace/dashboard summary (view-model + display + tests).
  Migration 0004 applied live (0003→0004); the seed backfilled to `default`.
- **Milestone E closed — live proof** (host backend, `AUTH_PROVIDER=jwt`, real stack): alice@acme
  POST → 201 owner=alice tenant=acme; alice@acme GET → 200; **alice@other (same subject, foreign
  tenant) → 403 `authorization.denied`**; the migration-backfilled seed → 200 for koray@default.
  The two release-gate identity items (ES-062) plus tenant isolation complete the milestone.
- Verification: `ruff` clean; `mypy app` strict clean (180 files); backend default **525 passed**
  / 22 deselected (+6); frontend 4-gate green (**74 tests**); `openapi.json` regenerated (create
  response gains `tenant`). TD: shared-knowledge per-tenant model, Tenant entity/membership,
  asymmetric JWT + refresh rotation, two-sessions-per-request refactor — all deferred/documented.

---

# Things Claude Must Never Do

- Invent business rules.
- Invent architectural responsibilities.
- Modify documentation through code.
- Compensate missing documentation with assumptions.
- Implement future tasks early.
- Introduce unnecessary abstractions.
- Introduce generic repositories.
- Introduce service locators.
- Modify completed architectural decisions.

---

# Development Workflow

For every ES:

Prompt
↓

Implementation Plan

↓

Architecture Review

↓

Implementation

↓

Verification

↓

Code Review

↓

Documentation Updates (if needed)

↓

Merge

↓

Next ES


---

# Architecture Timeline

## ES-002

- Backend application skeleton established.
- Application factory adopted.
- Shared exception infrastructure introduced.

---

## ES-003

- Technology-independent domain model implemented.
- Typed identifiers adopted.
- Value objects standardized.

---

## ES-004

- Persistence foundation established.
- Repository marker introduced.
- Multi-database infrastructure prepared.
- Redis defined as cache-only storage.

---

## ES-005

- Repository contracts moved to the Application layer.
- Investigation Service implemented.
- Business validation centralized in services.
- In-memory repositories adopted for application testing.

---

## ES-006

- Graph Service implemented (entities, relationships, neighbourhood traversal).
- Single graph repository adopted for the interconnected graph store (vs per-aggregate repositories for relational data).
- Idempotent entity creation: existing entities are reused by canonical identifier rather than duplicated, with an operational reuse log.
- Field-scoped updates (entity attributes, relationship confidence) modify only the intended field.
- Traversal limits (depth, max nodes) are resource bounds only and never alter graph semantics.
- Graph Service has no outbound dependency on the Investigation Service; relationship evidence references are not validated cross-service.

---

## ES-007

- Memory Service implemented as the authoritative MemoryItem system of record (PostgreSQL).
- Version-supersede + history pattern: update() appends a new sequential version; previous versions remain immutable; deprecate() changes only the latest version's status.
- get_history() returns versions ordered by version number ascending (deterministic).
- Embedding, semantic retrieval and synchronization explicitly deferred to the AI/RAG tasks (no AI-facing abstractions introduced).
- No outbound dependency on the Investigation or Graph services; MemoryItem references are structural only (not validated cross-service).

---

## ES-008

- Planner workflow/execution-plan contract first defined in documentation (single-action model; application-layer; stateless), then implemented.
- Planner Service implemented as a stateless, single-action orchestrator owning no data and no repository.
- Typed, representative Planner Action set (sealed union) dispatched via exhaustive `match`; full catalogue deferred to the Planner Agent (ES-011).
- Downstream service failures isolated into a FAILED execution result; the Planner Service depends on the Investigation/Graph/Memory services (application-layer orchestration, acyclic).
- Resolved the planner-agent vs planner-service contradiction in favour of the single-action decision loop.

---

## ES-009

- AI Runtime layer introduced (`app/ai/`) — foundation only: provider-neutral, replaceable provider ports.
- LLM provider port defined over minimal typed `LLMRequest`/`LLMResponse` (no raw string API); embedding provider intentionally single-text (batch deferred).
- Provider contracts are strictly provider-neutral (no OpenAI/Anthropic/Gemini-specific concepts); the AI layer imports only `typing`/`dataclasses` + the shared kernel.
- Per-provider error split (`LLMProviderError`, `EmbeddingProviderError`) under `AIRuntimeError`.
- Foundation owns only provider abstractions; prompt engineering, reasoning, orchestration and agent behaviour belong to higher AI layers. Concrete providers, AI config, agents and RAG deferred.

---

## ES-010

- Agent Runtime added to the AI Runtime layer: minimal, agent-neutral agent contract (`Agent` Protocol, `AgentIdentity`, typed `AgentRequest`/`AgentResult`) + a stateless `AgentRuntime` execution host.
- `AgentRequest.payload` is a generic framework-level input (no assumed "objective"); agent I/O kept AI-neutral (`investigation_id: str`, not a domain type).
- The runtime never propagates exceptions: `SentinelAIError` → FAILED result with the stable code; unexpected exceptions → FAILED result (`unexpected_runtime_failure`), logged but never surfaced; `BaseException` not caught.
- Provider-agnostic and stateless; AI layer imports only `typing`/`dataclasses` + the shared kernel; no domain/application/infrastructure coupling.
- Concrete agents, tools, Decision Engine, execution metadata/timing and rich context/output shapes deferred.

---

## ES-011

- Planner Agent contract documented first (planner-agent §4/§6/§13), then implemented as the first concrete agent.
- Typed contract `PlannerAgent.decide(InvestigationState, action_id) -> PlannerAction` over the ES-009 `LLMProvider`; generic AgentRuntime/AgentResult bridge deferred.
- `InvestigationState` is an application/AI-layer structure reusing ES-003 typed ids + `Confidence` (ubiquitous language), consumed already-assembled (agent never assembles it).
- Deterministic transformation: a minimal structured (JSON) provider response → one typed PlannerAction; invalid/unknown/malformed → ESCALATE fallback; prompt content is implementation-only.
- Representative action vocabulary (control + id-based); caller-supplied action ids.
- First deliberate AI → application (PlannerAction) and AI → domain (ids/Confidence) dependencies — the documented producer hand-off; no persistence access and no service calls.

---

## ES-012

- Memory Agent implemented as the second concrete agent (`memory-agent`), mirroring the ES-011 Planner
  Agent pattern: stateless, no persistence access, no service calls, fake-tested LLM provider.
- Scope decision (Option A — strategy selection): the agent reasons over an already-assembled
  `InvestigationState` and produces a typed `RetrievalPlan` declaring which documented retrieval
  strategies should participate; it never retrieves, coordinates sources or assembles context (those
  belong to the RAG Pipeline, ES-013).
- Typed contract `plan(InvestigationState, RetrievalPlanId) -> RetrievalPlan` over the ES-009
  `LLMProvider`; generic AgentRuntime/AgentResult bridge deferred.
- `RetrievalPlanId` introduced as an AI-layer typed identifier (mirrors the domain identifier style;
  caller-supplied, self-validating). `RetrievalStrategy` modelled as a **closed enum** because the
  documentation defines a fixed strategy vocabulary (vs the open string value objects used for
  genuinely open vocabularies).
- Deterministic transformation: a minimal structured (JSON) provider response → one typed
  `RetrievalPlan`. Unknown strategies are ignored while recognized strategies are preserved; the result
  is deduplicated and emitted in enum (canonical) order; an empty plan results only when no recognized
  strategy remains. Precondition violations (blank `RetrievalPlanId`, no objectives) raise
  `MemoryAgentError`.
- `InvestigationState` (ES-011) reused as the already-assembled input — the same assembly
  responsibility (rag §8); the ES-011 structure is neither moved nor modified. No AI → application
  dependency (narrower than ES-011); only AI → domain (`InvestigationId`).

---

## ES-013

- RAG Pipeline added to the AI Runtime layer (`app/ai/rag/`): the context-engineering core
  (rag-architecture §7 — the primary objective is context engineering, not retrieval).
- Scope decision (full pipeline): `Retriever → ContextBuilder → ContextValidation → PromptBuilder`,
  composed by a thin `RagPipeline.run(InvestigationState, RetrievalPlan) -> RagResult` orchestrator.
- Scope decision (single Retriever port): `Retriever` is a `Protocol`; the concrete source-backed
  retrievers (semantic/vector-store, structured/Memory, graph/Graph, external) are deferred and tested
  through an in-memory double. The AI layer takes no runtime dependency on backend services.
- Typed AI-layer structures: `RetrievedItem`/`RetrievedKnowledge` (with retrieval provenance —
  strategy, open `source` label, reference, content, `Confidence`), `InvestigationContext`,
  `ContextValidationResult` and `RagResult`. The Context Builder deduplicates by `(source, reference)`
  and emits a deterministic order (strategy enum order, source, reference).
- `PromptBuilder` is **provider-neutral**: it produces an AI-layer `Prompt` (not an `LLMRequest`),
  keeping prompt construction independent of the provider contract (rag §10/§19); the consuming agent
  wraps the `Prompt`. As a result `app/ai/rag` does not import the provider port at all.
- Validation issue codes modeled as a closed enum `ValidationIssueCode` (fixed vocabulary), consistent
  with the ES-012 closed-enum decision. Insufficient context is reported explicitly via
  `InsufficientContextError` (`RagError` base) rather than building a prompt over it.
- The pipeline performs no generation (produces the prompt only) and consumes the ES-012 `RetrievalPlan`
  + ES-011 `InvestigationState`. Only the `Retriever` port is injected; the stateless
  context-engineering components are owned by the pipeline (no service locator).

---

## ES-014

- API Foundation established under `app/presentation/api/`: the cross-cutting HTTP layer the resource
  APIs (ES-015+) build on. The API stays a thin communication boundary — no business logic, no service
  or persistence access.
- Scope decision (full foundation): versioned router + standard response/error envelope + request-context
  middleware + request-id-bearing error translation. Auth/authz (ES-019/020), rate limiting, pagination
  and caching are out of scope.
- `RequestContextMiddleware` assigns a per-request `request_id` (uuid4) and a `correlation_id` (from the
  inbound `X-Correlation-ID` header, else the request id), stores them on `request.state`, echoes
  `X-Request-ID`/`X-Correlation-ID`/`X-Process-Time` response headers and logs request lifecycle events.
  Identifier/timestamp generation is a presentation/transport concern — the "no UUID/clock in
  domain/services" rule constrains the domain and services, not the HTTP boundary.
- Standard envelope (explicit-helper style, api-design §9): generic `ApiResponse[DataT]` + `ResponseMeta`
  with `build_success`; resource endpoints (ES-015+) wrap their service results explicitly. Errors use
  `ApiErrorResponse` + `build_error`; the exception handlers now return the request-id-bearing envelope.
- `ResponseStatus` modeled as a closed enum (`success`/`error`); `ResponseMeta.timestamp` is a `datetime`
  (Pydantic serializes it to ISO-8601), preserving type safety.
- `/api/v1` router mounted but empty (filled by ES-015+); `/health` kept unversioned/operational.
  Processing duration is exposed via the `X-Process-Time` header rather than the envelope. Stale
  "ES-016 (API Foundation)" comments corrected to ES-014.

---

## ES-015

- Investigation API added under `app/presentation/api/v1/investigation/`: the thin presentation layer
  over the Investigation Service (ES-005), exposing the full Investigation/Evidence/Finding/Report
  surface as `/api/v1/investigations...` resources (api-design §6/§8). Controllers contain no business
  logic — they parse, map, delegate and wrap.
- Scope decision (presentation-only): `get_investigation_service` is defined but unbound — it raises
  `ServiceNotConfiguredError` (503) because the concrete repository adapter is deferred (ES-005 TD).
  API tests bind in-memory repository doubles through FastAPI `dependency_overrides`, exercising the real
  controllers/schemas/envelope/error-translation end to end.
- Scope decision (API-generated ids/timestamps): resource id and `created_at` are generated at the
  transport boundary via small `IdGenerator`/`Clock` ports (`app/presentation/api/generation.py`, stdlib
  defaults, overridable in tests). This is a presentation concern — the "no UUID/clock in domain/services"
  rule is preserved (the service still receives caller-supplied values). Finding update uses PUT semantics
  (the client supplies the full representation, including `created_at`).
- DTO↔domain conversion lives in `schemas.py` (`to_domain`/`from_domain`); the request status fields are
  typed as domain enums so Pydantic performs structural validation.
- Error translation refined (api-design §11): `error_status.http_status_for` maps stable error codes to
  HTTP status via an explicit table built from the error classes' `.code` constants (NotFound→404,
  Duplicate/InvalidTransition→409, validation/ownership/blank/confidence/missing-evidence→422,
  ServiceNotConfigured→503, unknown→400, preserving ES-014's default). A `RequestValidationError` handler
  wraps structural failures into the standard envelope (422, `api.validation_error`).
- Dependency direction: presentation → application (Investigation Service + errors) → domain; no
  persistence/infrastructure dependency. Sub-resource get-by-id controllers verify path ownership (404 on
  mismatch); no single-finding GET (the service exposes no `get_finding`).

---

## ES-016

- Graph API added under `app/presentation/api/v1/graph/`: the thin presentation layer over the Graph
  Service (ES-006), exposing the full entity/relationship/neighbour surface as `/api/v1/graph...`
  resources. Reuses the ES-014/015 foundation wholesale (envelope/context, `error_status`, `generation`,
  `ServiceNotConfiguredError`, `dependency_overrides` testing).
- Scope decision (presentation-only): `get_graph_service` is unbound — it raises
  `ServiceNotConfiguredError` (503) because the concrete Neo4j adapter is deferred (ES-006 TD); tests bind
  an in-memory `GraphRepository` double.
- Identifier decision (domain-driven divergence from ES-015): **entity id is client-supplied** — the
  entity's canonical identity (Domain Rule 3) — so the Graph Service's documented idempotent reuse works
  through the API. **Relationship id and `created_at` are API-generated** (no natural key) via the
  `IdGenerator`/`Clock` ports, consistent with ES-015.
- `create_entity` returns a uniform 201: the frozen ES-006 contract does not signal create-vs-reuse, and
  distinguishing it would require either a contract change or a racy pre-existence probe, so reuse is
  transparent (documented decision).
- `find_neighbors` applies basic transport validation only (`depth >= 1`, `max_nodes >= 1` via
  `Query(ge=1)`); no arbitrary upper bound — traversal/resource semantics stay in the Graph Service.
- Error translation: `graph.entity_not_found`/`graph.relationship_not_found` added to the
  `error_status` table (→ 404). DTO↔domain conversion lives in `schemas.py`; dependency direction is
  presentation → application (Graph Service + errors) → domain, with no persistence/infrastructure
  dependency.

---

## ES-017

- Memory API added under `app/presentation/api/v1/memory/`: the thin presentation layer over the Memory
  Service (ES-007), exposing the full Memory Item lifecycle (create, get, version-supersede update,
  deprecate, history) as `/api/v1/memory...` resources. Reuses the ES-014/015/016 foundation wholesale.
- Scope decision (presentation-only): `get_memory_service` is unbound — it raises
  `ServiceNotConfiguredError` (503) because the concrete PostgreSQL MemoryItem adapter is deferred
  (ES-007 TD); tests bind an in-memory `MemoryRepository` double that tracks every version.
- Version-supersede decision: `POST /memory` generates id + `created_at` and fixes `version=1`; `PUT
  /memory/{id}` takes the **full client representation including `version` and `created_at`** (PUT
  semantics, consistent with the ES-015 Finding update). The Memory Service enforces sequential versioning
  (`version == latest+1`; wrong version → 422 `memory.invalid_version`) — the API never invents the
  version. The path identifier is the single source of truth: `MemoryUpdateRequest` has no `id` field and
  `to_domain(*, id_value)` always takes the path id.
- `deprecate` is a body-less `POST /memory/{id}/deprecate` action; history is `GET /memory/{id}/history`
  (versions ascending). Memory error codes added to the `error_status` table
  (`memory.not_found`→404, `memory.duplicate`→409, `memory.invalid_version`→422).
- A dedicated test asserts the ES-007 immutable-history guarantee: after create + update, `GET /history`
  shows version 1 unchanged while version 2 reflects the update. Dependency direction:
  presentation → application (Memory Service + errors) → domain; no persistence/infrastructure dependency.

---

## ES-018

- Planner API added under `app/presentation/api/v1/planner/`: a single thin controller
  (`POST /api/v1/planner/actions`) over the single-action Planner Service (ES-008), reusing the
  ES-014/015 foundation. The request is a Pydantic discriminated union (`action` discriminator) mapping to
  a typed `PlannerAction`; the response projects the `ExecutionResult`.
- Scope decision (representative subset): only the control + identifier-based actions are exposed
  (`control`, `get_investigation`, `change_investigation_status`, `find_neighbors`, `get_memory`). The
  `Create*` actions (which embed full domain objects and duplicate the resource POST APIs) are deferred,
  consistent with the ES-008/011 deferral.
- Distinctive behaviour — failure isolation: the Planner Service returns downstream failures as a failed
  `ExecutionResult` (not an exception), so a valid action whose downstream fails returns **HTTP 200** with
  `execution_status="failed"` + `error`. Only a precondition violation (`InvalidActionError` → 422) or an
  unbound service (503) produces an HTTP error. The response field is named `execution_status` to avoid
  colliding with the ES-014 envelope's outer `status`.
- The response model is the generic `PlannerExecutionResponse[T]` (no large value union); the endpoint uses
  `PlannerExecutionResponse[object]` and Pydantic v2 serializes the projected resource models
  (`InvestigationResponse`/`EntityResponse`/`MemoryItemResponse`/control kind) by duck typing — keeping the
  type system open for future precise parametrization.
- `action_id` is API-generated (transport concern; echoed in the result for correlation).
  `planner.invalid_action` added to the `error_status` table (→ 422). Dependency direction:
  presentation → application (Planner Service + actions + errors) → domain; no persistence dependency.

---

## ES-019

- Authentication added at the API boundary (`app/presentation/api/auth.py`): the Authentication step of
  the request lifecycle (api-design §6). It only verifies identity — authorization (permission evaluation
  in the Application Domain) is ES-020 (auth ≠ authz).
- Technology-independent foundation (authentication-authorization.md is provider-neutral): `IdentityKind`
  (closed enum: human/system/external), `AuthenticatedIdentity` (subject + kind, self-validating), a
  replaceable `Authenticator` port (`authenticate(request) -> AuthenticatedIdentity`; provider extracts
  credentials and prescribes no protocol), and the default-deny `UnconfiguredAuthenticator`. The concrete
  identity provider is deferred.
- Scope decision (apply now, default-deny): `require_identity` is a router-level dependency on
  `api_v1_router`, so every `/api/v1` business endpoint requires a verified identity before execution
  (it runs before the endpoint's own service dependency, so an unauthenticated request returns 401 rather
  than 503). `/health` stays public. Secure by default — with no provider configured, all protected
  endpoints deny.
- `require_identity` records the identity on `request.state.identity` (continuity/traceability) and logs a
  traceable auth event (subject/kind + `request_id`, never the credential). `current_identity(request)` is
  the typed accessor parallel to `current_context` (raises rather than fabricating an identity).
- `AuthenticationError` (`api.unauthenticated`) added to the `error_status` table (→ 401); the existing
  envelope/handlers carry the request id. The ES-015–018 resource tests inject a test identity via
  `dependency_overrides[require_identity]` (and the not-configured tests pass auth to still reach the 503).

---

## ES-020

- Authorization added as the Authorization step of the request lifecycle (authentication-authorization.md
  §6/§7). The decision authority is the **Application Domain**: `app/application/authorization/` defines the
  `Authorizer` port, the `AuthorizationRequest` it evaluates, the `AuthorizationError` (`authorization.denied`
  → 403) and the default-deny `DenyAllAuthorizer`. The presentation never decides — it only triggers.
- Scope decision (apply now, default-deny): `require_authorization` (presentation) chains `require_identity`
  (authn → authz), builds the operation context and delegates to the application authorizer; with no policy
  configured it denies (least privilege). It is a router-level dependency on `api_v1_router`, so every
  `/api/v1` operation is evaluated: unauthenticated → 401 (authn first), authenticated-but-unpermitted →
  403. `/health` stays public.
- Clean dependency direction: `AuthorizationRequest` carries primitives (`subject`, `identity_kind`,
  `operation`), so the application authorizer never imports the presentation `AuthenticatedIdentity` — the
  ES-019 identity model is not relocated and the completed services (ES-005–008) are not modified.
- `require_authorization` records the `AuthorizationRequest` on `request.state.authorization` (so a denial is
  still observable to audit) and logs a traceable decision (subject/operation + `request_id`, never a
  credential). `build_operation(request)` centralizes the operation string; `current_authorization(request)`
  is the typed accessor parallel to `current_context`/`current_identity` (raises rather than fabricating).
- Test wiring: the ES-015–018 resource tests bypass the gate via `dependency_overrides[require_authorization]
  = lambda: None`; the ES-019 "passes through" tests run the real chain with an allow-all authorizer override.

---

## ES-021

- Audit added as the Backend's audit responsibility (audit-and-observability.md §4/§6), distinct from the
  observability request logging. `app/application/audit/` owns the capability: the `AuditEvent` model with
  the closed `AuditAction` (`operation.performed` / `authentication.failed` / `authorization.denied`) and
  `AuditOutcome` (`succeeded` / `denied` / `failed`) vocabularies, the `AuditRecorder` port and the default
  `LoggingAuditRecorder` (the durable, tamper-resistant store is deferred — the "Audit lifecycle" gap).
- Scope decision (apply now, logging recorder): a presentation `AuditMiddleware` records one audit event per
  protected `/api` request. It does **not** modify the ES-019/020 seams — it reads the `AuthorizationRequest`
  that `require_authorization` already stored on `request.state` (the exact purpose of the ES-020 refinement)
  plus the HTTP status, and derives who/operation/outcome (401 → authentication failed, 403 → authorization
  denied, else operation performed succeeded/failed). `/health` is not audited.
- Recording is best-effort: the `record` call is wrapped so a recorder failure is logged and swallowed — audit
  never drops a business request (`BaseException` is not caught). The recorder is held on `app.state.audit_recorder`
  (set in `create_app`, overridable in tests) since middleware cannot use FastAPI `Depends`.
- The `AuditEvent` carries primitives (`subject`, `identity_kind`, `operation`, `request_id`), so the
  application audit layer never depends on the presentation identity model. The middleware is added outermost
  so it observes the populated request state and the final response.

---

## ES-022

- Secrets Management foundation added (secrets-management.md): secrets are protected security assets, never
  configuration artifacts, never logged or embedded in business data. Technology-independent — the concrete
  vault/store is deferred. No live consumer exists yet, so it follows the ES-009 foundation pattern (ports
  defined, adapters/wiring deferred).
- `Secret` protection primitive added to the shared kernel (`app/shared/secret.py`): a hand-written class
  (deliberately not a frozen dataclass) that hides its value, masks `repr`/`str` to `Secret(********)` and
  exposes the value only through an explicit `reveal()` — the platform's technology-independent equivalent
  of `pydantic.SecretStr`, consumable by any layer (including the AI layer, per the ES-009 import rule).
- Application contract (`app/application/secrets/`): the typed `SecretName` reference (secret names are part
  of the system contract), the `SecretProvider` port (`resolve(SecretName) -> Secret`, need-to-know
  distribution, sync) and `SecretNotFoundError` (`secret.not_found`). Infrastructure
  (`app/infrastructure/secrets/`) provides the default `EnvironmentSecretProvider` (resolves from
  `os.environ`; missing/empty → `SecretNotFoundError`; the value is never logged).
- Dependency direction: `Secret` (shared) → stdlib; `SecretProvider`/`SecretName`/error (application) →
  shared; `EnvironmentSecretProvider` (infrastructure) → application + shared (the repository-port/adapter
  pattern). The existing `database.py` `SecretStr` configuration (ES-004) is left untouched — it already
  follows the least-exposure principle.

---

## ES-023

- Frontend established from scratch in `frontend/` (previously empty): **React 19 + TypeScript (strict) +
  Vite 6 (SPA) + React Router 7 + Tailwind 4** — the frontend counterpart of the backend ES-002 skeleton +
  ES-014 API foundation. React is the doc-endorsed framework (design-principles §9); SPA because ADR-009
  rejected server-rendered UI; the stack is documented here since the frontend architecture is
  framework-independent.
- Layered structure mirrors frontend-architecture §5/§7: `src/app` (Application: providers, router,
  `App`), `src/layouts`, `src/pages`, `src/sections`, `src/components` (+ `ErrorBoundary`, §11), `src/ui`
  (PrimitiveUI), `src/communication` (Communication layer) and `src/state` (minimal; ES-027 expands).
  Business logic stays in the backend; the frontend only consumes the Backend API.
- Communication layer (`apiClient`) is the single Backend API boundary (§10): a stateless typed fetch
  wrapper that resolves the base URL via `config.getApiBaseUrl()`, attaches the `Authorization` header from
  a pluggable `getAuthToken()`, applies an `AbortController` timeout, unwraps the ES-014 success envelope to
  return `data`, and maps the error envelope to an **immutable** `ApiError` (frozen, `readonly` code/message/
  requestId/status). Thin `get/post/put/delete` helpers wrap `request`. Envelope types mirror the backend
  `response.py` for a type-safe contract.
- App shell: `App` composes global providers + a top-level `ErrorBoundary` + the router; the router declares
  only a single `"/"` placeholder route (business routes added by ES-024+). The primitive `Button` is
  minimal (children/onClick/disabled/className).
- Verification discipline mirrors the backend (ruff/mypy/pytest): ESLint (flat config, typescript-eslint),
  `tsc -b` (strict, `noUncheckedIndexedAccess`/`noImplicitOverride`/`verbatimModuleSyntax`), Vitest +
  React Testing Library (9 tests) and `vite build` — all green. Vitest pinned to 3.x so it shares the
  top-level Vite 6 (avoiding a dual-Vite type clash). The backend is untouched (199 backend tests still
  pass).

---

## ES-024

- Investigation Dashboard implemented (dashboard-architecture.md) at `/investigations/:id`: the summary
  layer of the Investigation Workspace. It presents but never owns data — all information is fetched from
  the Backend API through the ES-023 communication layer.
- Composition (dashboard-architecture §4/§5): all six components are built modularly. Investigation Summary
  + Status (from the investigation) and Findings (from the findings API, filtered to confirmed
  validated/accepted per §5) render real data; Active Objectives, AI Insights and Recent Activity render
  explicit empty-state placeholders because the backend exposes no data source for them yet.
- Layer separation: the communication layer exposes typed `getInvestigation`/`listFindings` (DTOs mirroring
  the ES-015 responses, forwarding an `AbortSignal`) and a `toDashboardViewModel` mapper + a
  `loadInvestigationDashboard(id, signal)` loader that produce a UI-oriented `DashboardViewModel`. The page
  binds only to the view model — never to backend DTOs (the frontend counterpart of the backend
  to_domain/from_domain mappers). The `useInvestigationDashboard` hook is a minimal local fetch hook with
  `AbortController` cancellation; a server-state library (TanStack Query) is deferred to ES-027.
- States: loading, error (ApiError code/message + retry, preserving investigation context, §11) and loaded.
  `ConfidenceIndicator` conveys confidence as a bar **and** a percentage label (not colour alone, §17);
  `StatusBadge`/`FindingCard`/`SummaryItem` are reusable components.
- Demoability (user decision): **MSW** (Mock Service Worker) mocks the Backend API in the dev browser (the
  real `/api/v1` is auth-gated and the services are unbound), so `npm run dev` shows a fully populated
  dashboard — verified visually (preview screenshot, MSW `200 OK`, no console errors). This also resolved
  the earlier "white page" (the preview had opened the static `index.html` without the Vite dev server). MSW
  is dev/production-excluded (dynamic import under `import.meta.env.DEV`). In the jsdom test environment
  MSW's node interception was unreliable on this runtime, so the page integration tests mock the
  communication loader directly (16 frontend tests green: typecheck + lint + test + build). The backend is
  untouched.

---

## ES-025

- Investigation Workspace implemented (investigation-workspace.md) at `/investigations/:id/workspace`: the
  primary operational environment. It presents but never owns data — all information is fetched from the
  Backend API through the ES-023 communication layer; business logic stays in the backend.
- Composition (investigation-workspace §4/§5): coordinated, loosely-coupled regions. Overview, Evidence,
  Findings and a derived Timeline render real data; Graph is a placeholder (delivered by ES-026); AI
  Insights and Memory render explicit "not yet available" placeholders (no investigation-scoped backend
  source, consistent with ES-024).
- Scope decision (user-approved): a minimal, presentation-only **Investigation Context** (plain React
  context + reducer, page-scoped) holds the current selections and drives basic cross-region
  synchronization — selecting a finding highlights its supporting evidence (interaction-model §6, via the
  shared context, never region-to-region). The server-state cache (TanStack Query) and the promoted global
  store remain State Management (ES-027).
- Reducer decision: discriminated-union `WorkspaceAction` (`SELECT_FINDING`/`SELECT_EVIDENCE`/
  `CLEAR_SELECTION`) with an exhaustive `switch` + `never` guard; the pure state/reducer lives in
  `workspaceReducer.ts` (framework-free, independently tested), the provider/hook in `workspaceContext.tsx`.
- Reuse decision: `WorkspaceViewModel extends DashboardViewModel` — the shared investigation `summary` and
  the confirmed (validated/accepted) `findings` are reused as-is (investigation-workspace §5 presents
  "validated findings"), not redefined. Only `evidence`, `timeline` and the finding→evidence index are
  added. Timeline events and the index are Derived State (ui-state-management §5) produced by pure helpers
  (`deriveTimelineEvents`, `buildFindingEvidenceIndex`); the mapper only composes. The communication layer
  gains `EvidenceDto` + `listEvidence`.
- States: loading, error (ApiError code/message + retry, preserving investigation context, §11) and loaded.
  Evidence/finding cards convey selection through text and border (not colour alone, §17). Dashboard and
  workspace cross-link. The dashboard `FindingCard` stays untouched (a selectable `WorkspaceFindingCard`
  reuses `StatusBadge`/`ConfidenceIndicator`).
- Test-infra fix: React Testing Library auto-cleanup was not reliably registered on this runtime, so an
  explicit `afterEach(cleanup)` was added to the shared test setup (prevents rendered trees leaking across
  tests). MSW gains an evidence handler + sample evidence for the dev browser demo.
- Verification: 27 frontend tests green (lint + typecheck + test + build); browser demo verified via preview
  (populated workspace, finding→evidence highlight, all API mocks 200 OK, no console errors). The backend is
  untouched.

---

## ES-026

- Graph Visualization implemented (visualization-architecture.md) as the workspace **Graph Region** (replacing
  the ES-025 placeholder, inside the same `WorkspaceProvider` so it shares the Investigation Context). It
  presents but never owns data — entities/relationships come from the Backend Graph API (ES-016) through the
  ES-023 communication layer.
- Constraint-driven scope (user-approved): the backend Graph API is **entity-seeded** (no investigation→graph
  endpoint), so the graph is an **ego-graph** built from a seed entity's neighbourhood — `getEntity` +
  `listEntityRelationships` + `findNeighbors(depth=1, max_nodes=25)`, composed by `loadEntityNeighborhood`.
  The **seeds are derived from the confirmed findings' `related_entities`** (the only investigation-scoped
  entity source), so every seed is traceable to a presented finding.
- Rendering decision (user-approved): a hand-rolled **SVG node-link** diagram with a **deterministic radial
  layout** — zero new dependencies (visualization-architecture §6 technology-independence + "simplicity before
  abstraction"). Compute→render separation (refinement): pure `toGraphViewModel` (dedup + dangling-edge filter
  + seed flag), `calculateNodePositions` (seed centre, neighbours on a ring) and `calculateEdgeGeometry`
  (endpoint coordinates); `EntityGraph` only draws. Edges are directed (arrow marker) and type-labelled.
- Context extension (refinement): the Investigation Context gains `selectedSeedEntityId` + `selectedEntityId`
  with two additive discriminated-union actions — `SELECT_SEED_ENTITY` (chip → sets both) and `SELECT_ENTITY`
  (graph node → moves only the focus). Drilling into a node re-centers the graph while the **origin seed is
  preserved** (a firmer base for ES-027). This is additive; the ES-025 reducer/decision is unchanged.
- Synchronization (visualization-architecture §7): seed chips and graph nodes coordinate only through the
  shared context — regions never call each other. The focused entity's neighbourhood is loaded by
  `useEntityNeighborhood` (ES-025 hook pattern) with cancellation + a region-scoped retry (`reloadToken`,
  preserving context). AI Insights and Memory remain placeholders (no investigation-scoped source).
- Reuse: `WorkspaceViewModel` gains `seedEntities` via a pure `collectSeedEntities` (confirmed-finding
  classification shared with the dashboard through the new exported `isConfirmedFinding`). MSW gains three
  graph handlers + a small sample adjacency for the dev demo.
- Verification: 38 frontend tests green (lint + typecheck + test + build); browser demo verified via preview
  (findings-derived seed chips, seed → SVG ego-graph, node drill-down re-centers while the origin seed stays
  highlighted, all graph API mocks 200 OK, no console errors). The backend is untouched.

---

## ES-027

- State Management implemented (ui-state-management.md + frontend-architecture §8): the **four-category state
  architecture** (Investigation Context / View State / Session State / Derived State) with one owner each.
  Presentation only — business data stays in the backend and is cached, not owned.
- Server-state decision (user-approved): **TanStack Query** (`@tanstack/react-query` ^5), but kept behind a
  **thin `state/query.ts` boundary** — `createQueryClient`, the central `queryKeys`, the per-resource query
  option builders (`dashboardQuery`/`workspaceQuery`/`entityNeighborhoodQuery`, via v5 `queryOptions`, with
  `enabled`/staleTime/retry) and small invalidate helpers. The library is imported only in `query.ts`, the
  three server-state hooks and `providers.tsx`; pages/regions never touch it and never call
  `invalidateQueries` directly. This mirrors the single `apiClient` boundary and preserves technology
  independence (the docs define no server-state category — a documented gap).
- Hook refactor: `useInvestigationDashboard`/`useInvestigationWorkspace`/`useEntityNeighborhood` became thin
  adapters over `useQuery(builder(...))` projecting `{ viewModel|graph, loading, error, retry }`; `retry`
  routes through the invalidate helpers (not the client). The ES-026 `reloadToken` was removed. `toApiError`
  (shared in `communication/errors.ts`) centralizes the error normalization the hooks previously inlined.
- Session State (the missing category, user-approved): an app-level `SessionProvider` (mounted in
  `providers.tsx`) owns analyst preferences — concretely `theme` (dark/light), persisted to localStorage and
  applied via `:root[data-theme]` CSS variables, with a header `ThemeToggle`. Pure `sessionReducer`
  (discriminated-union actions) + `sessionSelectors` (`selectTheme`/`selectIsDark`/`selectIsLight`).
- Investigation Context stays workspace-owned (unchanged ES-025/026 store); its Derived-State reads are
  formalized as pure `workspaceSelectors` (`selectHighlightedEvidenceIds`, `selectIsTimelineEventEmphasized`)
  consumed by the Evidence/Timeline regions. View State stays region-local (documented pattern).
- Providers: `QueryClientProvider` (client via `useState(createQueryClient)`) + `SessionProvider` composed in
  `providers.tsx`. Test infra: a `TestQueryProvider` wraps the page/GraphSection tests; setup clears
  localStorage after each test (best-effort — the runtime's Web Storage lacks `clear`).
- Verification: 50 frontend tests green (lint + typecheck + test + build); browser demo verified via preview
  (theme toggle dark↔light persisted across navigation, dashboard/workspace/graph data served through TanStack
  Query, all API mocks 200 OK, no console errors). The backend is untouched.

---

## ES-028

- Docker implemented (deployment-architecture.md): the architectural deployment units (§5) are containerized
  for local/dev operation — **no application code changed**, only container/orchestration artifacts.
- Deployment-unit mapping: **Presentation** → `frontend` image, **Application** (incl. the in-process AI
  Runtime) → `backend` image, **Data** → `postgres`/`neo4j`/`qdrant`/`redis`. A standalone AI Runtime service
  does not exist yet, so it is co-located in the backend (deferred).
- Backend image (`backend/Dockerfile`): multi-stage, **wheel-based** (refinement) — the builder runs
  `python -m build --wheel` for a deterministic artifact; the runtime installs only that wheel (no dev extras,
  no build tooling), runs as a **non-root** user, and `HEALTHCHECK`s its own uvicorn over **loopback**
  (`127.0.0.1`, refinement). Startup opens no DB connections (lazy registry), so the container runs without
  live databases.
- Frontend image (`frontend/Dockerfile` + `nginx.conf`): multi-stage (Vite build → nginx). nginx serves the
  SPA (`try_files` fallback), long-caches Vite's content-hashed `/assets/` (`public, immutable`, refinement),
  and **reverse-proxies** `/api` and `/health` to `backend:8000` — the browser stays **same-origin**, so no
  CORS and the ES-014 API is untouched. `VITE_API_BASE_URL` is baked to the published origin
  (`http://localhost:8080`).
- Orchestration (`docker-compose.yml`, root): full topology defined; the **data tier is opt-in via a `data`
  profile** (refinement), so the default `docker compose up` runs backend + frontend and `--profile data up`
  adds the stores. The backend has **no `depends_on` on the data services** (lazy startup + avoids the
  Compose depends-on-a-profiled-service pitfall). Named volumes; `env_file: .env` with `required: false`
  (the app runs on code defaults). Reuses the existing `POSTGRES_/NEO4J_/QDRANT_/REDIS_` config + root
  `.env.example`.
- The prod frontend excludes MSW, so it calls the real (auth-gated, unbound → 401/403/503) backend and shows
  error states — expected until data/auth wiring lands (documented, not a defect).
- Verification: `docker compose config` validated for **both** the default and the `data` profile (correct
  service sets); root README gained a "Running with Docker" section. Image build/run (`docker compose build`
  / `up`) requires a running Docker daemon — Docker Desktop could not be started non-interactively in the
  session, so build/run is left for the user's Docker. Application test suites are unaffected (no app-code
  change).

---

## ES-029

- Configuration implemented (configuration-management.md): the backend's Configuration Management model is
  completed by adding the two missing pieces — the **Environment Configuration** type (§5) and the
  **Configuration Validation** lifecycle stage (§8) — **additively**; Platform Configuration (`settings.py`)
  and Domain Configuration (`database.py`) are unchanged.
- Environment type: `config/environment.py` introduces a typed, **closed-enum** `Environment`
  (development/test/staging/production, aligning environment-architecture §5) with an `is_production_like`
  helper (refinement) that centralizes the "non-development" distinction, and `resolve_environment` (case/
  whitespace-insensitive; unknown → `UnknownEnvironmentError`). `Settings` gains a typed `environment`
  property derived from the untouched `app_env` field.
- Configuration Validation: `config/validation.py` is **orchestration-only** (refinement) — `validate_environment`
  and `validate_secrets` are small pure functions composed by `validate_configuration`, each independently
  testable and easy to extend. In any production-like environment it rejects secret-bearing settings left at a
  known insecure default (`change_me`, kept in a private set) for `POSTGRES_PASSWORD`/`NEO4J_PASSWORD`;
  development is lenient. Errors (`config/errors.py`) derive from `SentinelAIError` with stable dotted codes
  (`config.unknown_environment`, `config.insecure_secret`); `InsecureSecretError` carries **only the setting
  name** (refinement) — never a secret or placeholder value.
- Wiring: `lifespan.py` runs `validate_configuration(...)` at **startup** (fail-fast before serving) and logs
  the resolved `Environment`. `create_app`/`main.py` are untouched; dev-default tests are lenient, so the
  existing suite is unaffected. Root `.env.example` documents the `APP_ENV` vocabulary + the non-dev secret
  requirement.
- Verification: from `backend/` — `ruff check .` clean, `mypy app` (strict) clean (119 files), `pytest`
  **214 passed** (15 new deterministic config tests). End-to-end in containers (rebuilt backend image):
  production + placeholder secrets → **fail-fast** (`InsecureSecretError` naming only the setting, exit 3);
  development (default) and production + real secrets → **start cleanly** (validated environment logged). The
  frontend is untouched.

---

## ES-030

- Deployment implemented (deployment-architecture.md + release-management.md): the concrete deployment/release
  automation the technology-independent docs leave open, realizing Release Readiness/Validation (§5/§8).
- CI (`.github/workflows/ci.yml`, user-approved): GitHub Actions on `push`/`pull_request` with **one job per
  deployment unit** (deployment independence): `backend` (`ruff` / `mypy` strict / `pytest`), `frontend`
  (`lint` / `typecheck` / `test` / `build`), and `images` (`docker compose build`, `needs: [backend, frontend]`)
  — the images are built to **validate the deployment artifacts only** (no registry push; no environment
  deploy — no target defined).
- Environment-specific deployment config (user-approved): `docker-compose.prod.yml` — the Operational-stage
  overlay (release-management §5) layered on the base compose. It forces `APP_ENV=production` + restart
  policies, so with a real `.env` the ES-029 validation guards production (fail-fast on placeholder secrets).
  Run as `docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile data up -d`.
- Curated documentation updates (user-approved, applied as a distinct first step): five additive architectural
  clarifications — server-state (cached backend data) as a distinct concern (frontend-architecture §8 +
  ui-state-management §5), the Timeline event source and the AI Insights/Memory data dependency
  (investigation-workspace §5), and the entity-seeded graph model (visualization-architecture §5). Each doc was
  bumped to v1.1.0 with a Version History row. The technology-independent "gaps" (concrete container/orchestration
  guidance, concrete config-validation rules, Session-State persistence, the CORS/edge contract) were
  deliberately left unchanged to preserve Architecture-Before-Framework.
- Verification: CI YAML parses (3 jobs, `push`/`pull_request`); the prod overlay merges correctly
  (`APP_ENV=production` + restart on the backend). The CI job commands are already green locally — backend
  **214** (ruff/mypy/pytest), frontend **50** (lint/typecheck/test/build), and `docker compose build` (both
  images). No application code changed.

---

## ES-031

- Observability implemented (platform-observability.md + audit-and-observability §5/§8): operational Platform
  Observability, **distinct from the ES-021 security Audit** (which is untouched). Cross-cutting code lives in a
  new stdlib-only `app/observability/` package.
- End-to-end traceability: `app/observability/correlation.py` holds a `Correlation` (`request_id`/
  `correlation_id`) in a `contextvars.ContextVar`; `RequestContextMiddleware` binds it for the request (reset in
  `finally`) so **every log record emitted while handling a request is correlated**, not just the summary line.
- Structured logging (user-approved): `core/logging.py` gains a `JsonFormatter` and a `CorrelationFilter`;
  `configure_logging` selects `text|json` by resolving `settings.log_format`. Refinement 1: `LogFormat` is a
  **closed enum** (`config/log_format.py`, mirroring ES-029 `Environment`); an invalid `LOG_FORMAT` is **rejected
  fail-fast by the ES-029 `validate_configuration`** (`InvalidLogFormatError`, `config.invalid_log_format`),
  while `configure_logging` itself falls back to `text` leniently (never blocking startup, like the log-level
  fallback).
- Metrics (user-approved): `app/observability/metrics.py` is a minimal, **dependency-free** in-memory registry
  rendering the Prometheus text exposition (`sentinelai_requests_total{method,status}`, request duration
  sum/count, `uptime_seconds`). Refinement 2: `render()` copies an immutable snapshot **under the lock** then
  builds the text **outside** it, so producing the exposition never blocks request recording. The middleware
  records each request.
- Endpoints: `app/presentation/observability.py` adds `GET /health/ready` (readiness = startup completed /
  persistence registry present; **does not probe the DBs**, since the backend runs without them) and
  `GET /metrics` — unversioned, public operational endpoints (like `/health`, not auth-gated). Registered in
  `main.py`; `settings.log_format` + `.env.example` document `LOG_FORMAT=text|json`.
- Verification: from `backend/` — `ruff` clean, `mypy app` strict clean (124 files), `pytest` **228 passed**
  (14 new observability/config tests). End-to-end in the rebuilt backend container: `/health/ready` → 200
  ready; `/metrics` → Prometheus text with `sentinelai_requests_total`/uptime; with `LOG_FORMAT=json` the
  startup and request logs are single-line JSON carrying `request_id`/`correlation_id`. The frontend is
  untouched.

---

## ES-032

- Test Foundation implemented (testing-strategy.md): the shared validation foundation the specialized specs
  (ES-033 Architecture, ES-034 Integration, ES-035 AI) build on. The mature existing suites (backend 228,
  frontend 50) are **left unchanged**; the foundation is additive.
- Validation taxonomy (testing-strategy §5/§6): pytest `markers` (`unit`/`integration`/`architecture`/
  `operational`) registered in `pyproject.toml` with `addopts = "--strict-markers"` (an unregistered marker
  decorator is an error). `pytest -m unit` selects a category. Frontend categorization stays directory/naming
  based (Vitest has no markers).
- Shared support (user-approved — scaffold, no rewrites): `backend/tests/support/` provides reusable in-memory
  repository doubles for the Investigation family + deterministic `SequentialIdGenerator`/`FixedClock`
  (`doubles.py`) and **pure, immutable** builders + `make_investigation_service()` (`builders.py`, refinement 1:
  each call returns a fresh independent object, no shared mutable state / mutable defaults). `tests/foundation/
  test_support.py` (marked `unit`) exercises it, so the infrastructure is validated and the reuse pattern is
  demonstrated for ES-034.
- Coverage (user-approved — measure/report, no gate): `pytest-cov` (backend) + Vitest v8 coverage (frontend),
  written to **fixed report paths** (`backend/htmlcov`, `frontend/coverage`, refinement 2) and published as CI
  artifacts (`actions/upload-artifact`, `if: always()`); **no `--cov-fail-under`/threshold** — quality
  confidence is architectural assurance, not a coverage percentage (testing-strategy §7/§8). `.gitignore` covers
  the report paths.
- `TESTING.md` documents the taxonomy, ownership, shared support, how to run/select and coverage.
- Verification: backend `ruff` clean, `mypy app` strict clean (124 files — tests are outside `app`), `pytest`
  **233 passed** (228 + 5 foundation), `-m unit` selects 5/deselects 228, coverage ~97% reported +
  `backend/htmlcov/index.html` written. Frontend `test:coverage` **50 passed** + `frontend/coverage/index.html`
  written; `lint`/`typecheck`/`build` green. CI YAML parses (3 jobs).

---

## ES-033

- Architecture Tests implemented (architecture-testing.md): independent, **static** verification that the
  implementation preserves the Clean Architecture boundaries and Permanent Engineering Decisions, using the
  `architecture` marker registered in ES-032 (Architecture Validation, testing-strategy §5). No modules are
  imported to run the checks — each `app/*.py` file is parsed with `ast`.
- Backend (`tests/architecture/test_architecture.py`, 7 tests): **Boundary Validation** — the domain depends
  only on the domain + the shared kernel; the application imports no infrastructure/presentation; the AI Runtime
  imports no infrastructure/presentation (never accesses persistence directly); presentation does not import
  infrastructure directly; the shared kernel has no `app` dependency. **Constraint Validation** — the domain and
  services generate no identifiers (no `uuid`) and read no clock (no `datetime.now`/`utcnow`), enforcing the
  caller-supplies-ids/timestamps decision. All boundaries were calibrated against the current code first (they
  hold and now guard against erosion).
- Frontend (`src/architecture.test.ts`, 1 test): the Communication layer is the single Backend API boundary
  (Frontend Architecture §10) — `fetch` appears only under `communication/`. The source is scanned at build time
  via `import.meta.glob(..., { query: "?raw", eager: true })`.
- Verification: backend `ruff` clean, `mypy app` strict clean (124 files), `pytest` **240 passed** (233 + 7
  architecture), `-m architecture` selects 7/deselects 233. Frontend `lint`/`typecheck`/`test` (**51 passed**,
  50 + 1 architecture)/`build` green. No application code changed (tests only).

---

## ES-034

- Integration Tests implemented (integration-testing.md): cross-domain **Integration Validation** using the
  `integration` marker registered in ES-032. The doc is deliberately technology-independent, so the concrete
  scope was chosen as the architectural seams that exist today, verified **in-process** over the shared
  in-memory doubles (the persistence adapters are still deferred — live-DB integration follows them).
- Shared support extended as ES-032 planned: `tests/support/doubles.py` gains `InMemoryGraphRepository` +
  `InMemoryMemoryRepository` (version-aware: add appends, get returns latest, update replaces in place,
  list_versions ascending); `tests/support/builders.py` gains `build_entity`/`build_relationship`/
  `build_memory_item` + `make_graph_service()`/`make_memory_service()`. Existing suites intentionally not
  migrated.
- `tests/integration/` (11 tests, all `pytest.mark.integration`), three collaboration areas:
  **(1) presentation ↔ application ↔ domain** (`test_api_investigation_flow.py`) — the full investigation
  lifecycle through the real HTTP stack (create → activate → evidence → finding → report) with cross-resource
  consistency and envelope/request-id threading, plus cross-resource error translation (foreign evidence →
  422 `investigation.evidence_ownership`, unknown evidence → 404).
  **(2) Planner orchestration across service boundaries** (`test_api_planner_orchestration.py`) — one app
  binds the Investigation/Graph/Memory/Planner APIs over the *same* service instances: a planner-effected
  status change is visible through the resource API; the planner traverses graph data created via the Graph
  API and reads memory created via the Memory API; one downstream failure surfaces per-boundary (404 at the
  resource API vs the ES-018 failure isolation: HTTP 200 + `execution_status="failed"`).
  **(3) AI ↔ application hand-off** (`test_ai_application_handoff.py`) — Planner Agent (scripted fake LLM) →
  typed `PlannerAction` → Planner Service execution (including the malformed-response → ESCALATE degradation);
  Memory Agent → typed `RetrievalPlan` → RAG pipeline (plan honored by the retriever, provenance in the
  prompt; empty plan → `InsufficientContextError`). No new orchestrator introduced — the deferred composition
  stays deferred.
- Test-infra note: FastAPI `dependency_overrides` lambdas must capture doubles via **closures**, not
  default-argument values — FastAPI/pydantic treats a defaulted lambda parameter as a request parameter and
  copies the default per request, silently splitting state across requests.
- `TESTING.md` updated (support inventory + integration suite location). No application code changed
  (tests only).
- Verification: `ruff` clean, `mypy app` strict clean (124 files), `pytest` **251 passed** (240 + 11
  integration), `-m integration` selects 11/deselects 240.

---

## ES-035

- AI Validation implemented (ai-validation.md): **behavioral validation** of the AI capabilities against
  their architectural responsibilities, over deterministic scripted provider doubles (no live AI). The doc
  prescribes no evaluation mechanics, so the concrete scope is the architectural behavior the ES-009–013
  contracts establish: typed decision contracts, safe degradation, behavioral consistency, responsibility
  alignment and explainable provenance.
- Taxonomy extension: a fifth pytest marker **`ai`** registered in `pyproject.toml`. Rationale:
  ai-validation.md is a peer specification of architecture-testing.md / integration-testing.md, which both
  have markers in the ES-032 taxonomy; AI Validation had none — a consistency gap resolved additively
  (testing-strategy §5's four areas are unchanged; `ai` realizes the separate AI Validation model).
- `tests/ai_validation/` (18 tests, all `pytest.mark.ai`) mirrors the doc's four validation areas:
  **Agent Validation** — stable agent identities, statelessness across interleaved executions, and the
  AgentRuntime's failure containment as a behavioral guarantee over failure classes (domain error → stable
  code; unexpected → `unexpected_runtime_failure`; nothing escapes).
  **Planner Validation** — a curated adversarial provider-response matrix (`ADVERSARIAL_RESPONSES` in
  `tests/ai_validation/support.py`) always resolves to exactly one typed `PlannerAction` carrying the
  caller's `action_id`; unrecognized output **escalates, never auto-completes**; repeated decisions are
  identical; a provider-injected foreign investigation id cannot redirect the decision (the action targets
  only the assembled state); a `RecordingLLM` proves the reasoning input derives from the Investigation
  State (id + objectives present in the prompt).
  **Memory Validation** — the same matrix always resolves to exactly one typed `RetrievalPlan` (unrecognized
  → empty selection, never an invented strategy); partial recognition preserves recognized strategies;
  selection is canonical-order + deduplicated and repeat-consistent; the plan is bound to the caller's
  investigation/plan ids; reasoning input verified as with the Planner.
  **Knowledge Validation** — the assembled context and prompt are invariant to retrieval order; every
  knowledge item stays traceable in the prompt (strategy/reference/content — provenance/explainability);
  the validation gate refuses insufficient context (empty knowledge, missing objectives) so no prompt is
  ever built over it; pipeline runs over equal inputs are repeatable.
- `TESTING.md` updated (taxonomy table + `ai` row). No application code changed (tests + one marker
  registration only).
- Verification: `ruff` clean, `mypy app` strict clean (124 files), `pytest` **269 passed** (251 + 18 ai),
  `-m ai` selects 18/deselects 251.

---

## ES-036

- Performance & Reliability implemented (performance-reliability.md): **operational sustainability
  validation** realizing the doc's four areas as architectural assurance — deliberately **no load testing,
  no latency thresholds, no benchmark metrics** (the doc excludes benchmarking tools and implementation
  performance metrics; operational confidence is architectural assurance, §3/§4).
- `tests/operational/` (8 tests, all `pytest.mark.operational`):
  **Reliability** (`test_reliability.py`) — 25 repeated requests behave identically with unique per-request
  ids; the correlation contract holds across sustained use; failing business traffic (unbound → 503)
  interleaves with healthy operational traffic without degradation; the metrics counters grow monotonically
  with traffic.
  **Resilience** (`test_resilience.py`) — an unexpected in-request failure is contained to that request
  (500 `internal_server_error` envelope, failure detail never leaked, `raise_server_exceptions=False` so the
  server-side containment itself is under test); containment is identical across repeated failures; the
  operational surfaces (`/health`, `/health/ready`) keep serving throughout.
  **Scalability** (`test_scalability.py`) — 50 concurrent service operations stay isolated and individually
  readable (stateless services over repository-driven state); contended metric recording (8 threads × 250
  records with interleaved rendering) loses no observation (exact final counts).
- Taxonomy completion: the `operational` marker (registered ES-032, previously unapplied) is now **applied to
  the existing operational suites** — `test_health.py`, `test_observability_api.py`,
  `tests/observability/*` and `tests/config/test_configuration.py` (`pytestmark` + `import pytest` only; no
  test bodies changed). `-m operational` now selects the full Operational Validation category (38).
- Test-infra note: `/health/ready` requires the lifespan — operational tests that assert readiness use
  `with TestClient(app)` so startup actually runs.
- `TESTING.md` updated (specialized suite locations; the stale "markers applied by ES-033/034" note
  replaced). No application code changed (tests only).
- Verification: `ruff` clean, `mypy app` strict clean (124 files), `pytest` **277 passed** (269 + 8
  operational), `-m operational` selects 38/deselects 239. All 36 ES complete — the implementation plan is
  fully delivered.
---

## ES-037

- AI Composition implemented (ADR-010; architecture-audit Phase 1 — "composition gap"): the AI Runtime
  now owns the compositions that connect agents to executors, in `app/ai/orchestration/`.
- **Investigation Loop** (`loop.py`) — the Planner decision loop: Planner Agent decides one action,
  the action executor (Planner Service in production, behind the `ActionExecutor` port) executes it,
  the next Investigation State is observed through the `StateAssembler` port, and the cycle repeats
  until a control action (complete → `COMPLETED`, escalate → `ESCALATED`) or the caller-supplied cycle
  budget ends the run (`EXHAUSTED`). Control actions are executed through the same boundary so every
  planner decision stays observable. Stateless; ids caller-supplied via `ActionIdSource` (no UUID
  generation); failed execution results never terminate the loop — the agent observes and decides
  (planner-agent §12); `PlannerAgentError` preconditions propagate. New `InvestigationLoopError`
  (`ai.investigation_loop_error`) for a non-positive budget.
- **Retrieval Flow** (`retrieval.py`) — Memory Agent → RAG Pipeline composition (closes the ES-013
  "Memory Agent ↔ pipeline composition" deferral): selects strategies, then executes them into a
  validated context + prompt; adds no behaviour of its own.
- **Architecture tests extended** (mirroring the new architecture-testing.md §6 catalogue): AC-04
  (`application` must not depend on `app.ai` — ADR-010 one-way composition direction) and AC-07
  (no service imports another service's `repositories` — ADR-004) are now mechanically enforced.
- Documentation: ADR-010 created (+ index); planner-service.md v2.0.0 single-model rewrite;
  api-design.md v1.1.0 alignment; architecture-testing.md v1.1.0 normative constraint catalogue.
  Audit and two-phase remediation plan recorded in `SentinelAI-Architecture-Audit-Plan.md`.
- Verification: `ruff` clean, `mypy app` strict clean (127 files), `pytest` **289 passed**
  (277 + 8 loop + 2 retrieval flow + 2 architecture).


---

## ES-038

- Audit Remediation Phase 2 implemented (architecture-audit plan, `SentinelAI-Architecture-Audit-Plan.md`):
  the remaining audit findings (A3, A4, A5/B5, A7, A9, A10, B3, B6, B8, B10) closed through governance and
  documentation alignment, plus one doc-driven lifecycle code change.
- **ADR-011** (new): supporting-persistence category (never authoritative); Redis governed under it,
  demand-driven integration; amends ADR-003. Index updated.
- **Documentation aligned** (all with version bumps + history entries): database-architecture v1.1.0
  (sync = derived representations only, owned by the owning service; "SyncService" removed; §8a cross-store
  reference rules), rag-architecture v1.1.0 + memory-architecture v1.1.0 (Memory Agent = strategy selector,
  Retrieval Flow composition per ADR-010), domain-model v1.1.0 + investigation-service v1.1.0 (Finding
  lifecycle fixed; Suspended/reopen transitions defined; "close" = complete), dashboard-architecture v1.1.0
  ("confirmed finding" = Validated|Accepted, presentation-filter ownership), agent-architecture v1.1.0 +
  planner-agent v1.1.0 (Investigation Workspace terminology), api-design (Planner Action Resource declared
  transitional/non-contractual, mirrored in the router docstring), ADR README (decision-specific rationale
  standard, ADR-010 onward), README.md (AI Runtime row de-LangChain'd to the decided provider-neutral
  runtime).
- **ThreatGraph** recorded in Deferred Decisions (ADR-007 remains Accepted; no implementation, now tracked —
  audit B6).
- **Code (doc-driven):** `InvestigationService._ALLOWED_TRANSITIONS` extended per investigation-service
  v1.1.0 (Active ↔ Suspended, Suspended → Archived, Completed → Active reopen); `domain/enums.py`
  inconsistency note removed; 4 new lifecycle tests (suspend/resume, suspended-cannot-complete-directly,
  reopen, archived-terminal). Planner router docstring carries the transitional contract status.
- Resolved Open Documentation Gaps: "SUSPENDED state transition definition", "Investigation 'Close'
  lifecycle state" (list above retained as historical record).
- Verification: `ruff` clean, `mypy app` strict clean (127 files), `pytest` **293 passed** (289 + 4
  lifecycle).
---

## ES-039

- Gap closure implemented (architecture gap analysis `ARCHITECTURE-GAPS-2026-07-03.md`; scope
  exclusion honored: no concrete DB adapters, no provider keys).
- **Investigation Trace (M-01/E-07)**: `domain/trace.py` (`TraceEntry`, `TraceEntryKind`,
  `TraceEntryId`); append-only `TraceRepository` port + `record_trace`/`list_trace` on the
  Investigation Service; the Investigation Loop records decision/execution/outcome entries and the
  Retrieval Flow records retrieval entries through the best-effort `TraceSink` port (trace failures
  never break the flow).
- **Outcome contract (M-07)**: `OutcomeRepository` port + `create_outcome`/`get_outcome` (0..1 per
  investigation, contributing findings validated).
- **Single execution path + resilience (ADR-013, E-02/D-03)**: typed generic `Agent`/`AgentResult`
  (PEP 695), `AgentRuntime.run` as the only host (agents raise; runtime contains); typed
  `PlannerDecisionRequest`/`RetrievalPlanRequest` + `execute` on both agents; the loop degrades to
  `ESCALATED` with a stable `failure_code` on agent/provider failure (proven by broken-LLM tests);
  the Retrieval Flow re-raises contained failures as `MemoryAgentError` with the code; provider
  ports carry the bounded-execution contract; new `ExternalKnowledgeProvider` port (M-03/E-04) and
  `ExternalKnowledgeError`.
- **Contract artifact (E-05)**: `backend/scripts/export_openapi.py` → committed
  `docs/api/openapi.json` (2.7k lines) + `test_openapi_contract.py` freshness check
  (architecture-marked; AC-15).
- Tests: agent-runtime suite rewritten for the typed contract; loop suite extended (provider-failure
  degrade, precondition degrade, trace recording, best-effort sink); retrieval-flow suite extended
  (trace entry, contained provider failure); investigation-service suite extended (5 outcome + 3
  trace tests); all construction sites rewired with the two new repositories (support doubles
  `InMemoryOutcomeRepository`/`InMemoryTraceRepository`).
- Verification: `ruff` clean, `mypy app` strict clean (130 files), `pytest` **304 passed**
  (293 → 304: +8 service, +2 loop, +2 flow, +1 contract, −2 legacy runtime envelope tests).

---

## ES-040

- PostgreSQL persistence implemented for the Investigation family (first vertical slice, plan §3):
  Alembic baseline migration `0001` (investigation, evidence, finding, report, investigation_outcome,
  trace_entry — domain-named tables; the plan's "outcome/trace" shorthand), typed SQLAlchemy 2.0 ORM
  rows, pure domain↔row mappers and six repository adapters realizing the frozen application ports
  (AC-01/02/05/07/08/09 preserved; no domain change).
- **Transaction model**: adapters are bound to one caller-supplied `AsyncSession`; the whole adapter
  set of a request shares it, so *one service operation = one local transaction* whose
  commit/rollback boundary is owned by the request scope (`session_scope`, bound in ES-042). Writes
  `flush()` so constraint violations surface inside the owning operation.
- **Schema decisions**: single shared declarative `Base` with a deterministic constraint naming
  convention (hand-written baseline ≡ future autogenerate); lifecycle states stored as their stable
  string values (no DB enum types); identifier lists as PostgreSQL text arrays; `timestamptz`
  timestamps (callers already supply tz-aware values); FKs only within the service's own schema
  (children → investigation); `investigation_outcome.investigation_id` UNIQUE enforces the 0..1 rule
  at the database level; `outcome.report_id` deliberately a plain column (the service does not
  validate it — the schema is no stricter than the owning service); cross-service references stay
  identifier-only (database-architecture §8a — no FK from any other service's schema).
- **Append order materialized**: `trace_entry.seq` is a server-generated `Identity` column;
  `list_for_investigation` orders by it — never by caller-supplied timestamps — realizing the
  append-only/append-ordered trace contract (domain-model §11b). List reads elsewhere use
  deterministic `(timestamp|created_at, id)` ordering.
- **Live validation strip**: new opt-in `live` pytest marker (default run deselects it via `addopts
  -m "not live"`, so the standard suite stays database-free); `tests/live/` (plain functions,
  migrate-to-head once per process + per-test truncation; 5 investigation-family tests incl.
  empty-database migration determinism, full lifecycle across real transactions, array round-trips,
  DB-level outcome uniqueness below the service, append-order trace); CI gains the `backend-live`
  job (PostgreSQL service container, `pytest -m live`); compose publishes the `data`-profile
  Postgres on loopback `127.0.0.1:5432` for host-run live tests; TESTING.md documents the category.
- Verification: `ruff` clean, `mypy app` strict clean, `pytest` 304 passed / live deselected.
  Docker Desktop could not be started non-interactively in this session (ES-028 constraint), so the
  live run is delegated to the CI strip / user Docker (recorded as ES-040 TD).

---

## ES-041

- Versioned MemoryItem PostgreSQL adapter implemented (ES-007 TD adapter part): `memory_item` table
  with **one row per version and composite primary key `(id, version)`** — the version-supersede
  pattern becomes a plain insert, historical versions stay immutable rows; migration `0002`.
- Port semantics realized exactly (`MemoryRepository`): `add` inserts a version row; `get` selects
  the highest version; `list_versions` orders ascending; `update` merges in place on `(id, version)`
  — used only for the latest-version status change (deprecation), per the frozen contract.
- No FK to `investigation`: `source_investigation_id` is a plain identifier — cross-service
  references are identifiers only (database-architecture §8a); dangling references stay observable
  rather than DB-rejected.
- Embedding/semantic/Qdrant deliberately untouched (ADR-012 — second slice).
- Live test: full versioned lifecycle against real PostgreSQL (version sequence via service
  create/update, gap rejection, latest-wins `get`, deprecation touching only the latest version,
  lossless ascending history) — in the opt-in `live` suite (CI `backend-live`).
- Verification: `ruff` clean, `mypy app` strict clean, `pytest` 304 passed / live deselected.

---

## ES-042

- Runtime persistence binding implemented — the 503 era ends for the slice's stores: the
  Investigation, Memory and Planner services are provided over the concrete PostgreSQL adapters at
  runtime (ES-015/017/018 TD "runtime binding" closed; ADR-008 delegation now live).
- **Composition root**: `app/dependencies/services.py` builds the request-scoped service graph and
  `create_app` attaches it via `FastAPI.dependency_overrides` — the presentation dependency modules
  keep their explicit unbound default (503) and never import infrastructure (AC-05); tests that
  install their own overrides after `create_app` still win, so the existing double-driven suites
  are unaffected.
- **One request = one session = one transaction**: every provider opens one `session_scope` session;
  the Planner composition shares it across its Investigation and Memory services. The Graph
  dependency is the **explicit-contract unavailable repository**
  (`infrastructure/persistence/neo4j/unavailable.py`): every operation raises the new
  `GraphStoreUnavailableError` (`graph.store_unavailable`), which the Planner Service isolates into
  a contained failed execution result (planner-service §8 — the slice's living failure-isolation
  proof); the Graph API endpoints stay explicitly unbound (503).
- **Stable failure contracts at the binding seam**: no registry (startup never ran) →
  `api.persistence_not_configured` (unchanged code, so the lifespan-less presentation tests held);
  registry present but PostgreSQL unreachable → connectivity failures
  (`OperationalError`/`InterfaceError`/`OSError`) are translated to the new
  `api.persistence_unavailable` (503) — an operational condition with a stable code, never a leaked
  driver exception; data-level errors (e.g. `IntegrityError`) are deliberately not masked. Both new
  codes joined the `error_status` table.
- **Readiness reflects the bound store**: `/health/ready` now probes PostgreSQL through
  `PersistenceRegistry.ping_postgres()` (SELECT 1, 2 s timeout) — ready/ok only with a reachable
  store; `not_ready` distinguishes `not_initialized` from `unavailable`; `/health` (liveness) and
  the container healthcheck stay store-independent. The ES-031 "readiness = startup completion"
  behavior is superseded; the operational tests were updated to the new contract (the ready happy
  path moved to the live suite) and `docs/api/openapi.json` was regenerated (AC-15).
- Live E2E test (opt-in suite): real app + lifespan against live PostgreSQL — investigation
  create/status/evidence flow, versioned memory flow, planner `get_memory` completing against live
  data, `find_neighbors` returning HTTP 200 with `execution_status="failed"` +
  `graph.store_unavailable`, readiness ready/ok, Graph API still 503.
- Verification: `ruff` clean, `mypy app` strict clean (142 files), `pytest` **304 passed** / 7 live
  deselected; the connectivity-degradation path (`api.persistence_unavailable`) is exercised in the
  default suite (reliability test with lifespan and no store); live paths run in CI `backend-live`.

---

## ES-040/041/042 — Live verification addendum

- The live suite ran against real PostgreSQL (compose `data` profile, Docker started by the user in a
  follow-up session): **7/7 live tests green** alongside the 304-test default suite (ruff + mypy
  strict clean). Two issues surfaced and were fixed:
- **Test fix (migration determinism)**: the ES-040 test had hard-coded `alembic_version == "0001"`,
  stale the moment ES-041's `0002` became head; it now compares against
  `ScriptDirectory.get_current_head()`, so it stays valid as the migration chain grows.
- **Readiness probe timeout 2s → 5s** (`observability.py`): on Windows, `localhost` resolves
  IPv6-first while the published port listens on IPv4 only — the refused `::1` attempt costs ~2s per
  fresh connect, so a cold pool tripped the 2s probe. 5s absorbs the fallback; TESTING.md now
  recommends `POSTGRES_HOST=127.0.0.1` for host-run live tests (CI already uses it). The
  degradation semantics are unchanged (unreachable store still reports `not_ready`/`unavailable`).

---

## ES-043

- First concrete LLM provider implemented (decision K-1): `infrastructure/ai/gemini.py` realizes the
  provider-neutral `LLMProvider` port over the Gemini `generateContent` REST API via **httpx** — no
  vendor SDK (one endpoint, one JSON shape, explicit error mapping; httpx promoted to a declared
  runtime dependency, already present transitively). The AI layer stays provider-neutral; the
  adapter is edge code in infrastructure.
- **ADR-013 realized in a real adapter**: every call runs under `asyncio.timeout` with the
  configured bound (httpx carries the same value as network timeout) — exceeding it, transport
  failures, non-200 statuses (Gemini quota/rate-limit 429 included), safety-blocked or
  candidate-less responses and malformed payloads all map to `LLMProviderError` with a bounded,
  key-free message.
- **Key hygiene / ES-022's first real consumer**: `GOOGLE_API_KEY` resolved through the
  `SecretProvider` port at construction (missing key → explicit `secret.not_found`, mapped 503);
  the key travels only as a request header (never in the URL, so URL-bearing exceptions cannot leak
  it) and appears in no error/log. Configuration via `config/ai.py` `GeminiSettings`
  (`GEMINI_MODEL` default **gemini-3.5-flash**, `GEMINI_TIMEOUT_SECONDS`, `GEMINI_TEMPERATURE`);
  the key is deliberately not a settings field.
- Contract tests over `httpx.MockTransport` (11, network-free): success/multi-part join, header-only
  key + URL hygiene, 429/500/safety-block/no-candidates/malformed/transport mappings, the
  execution bound (slow handler never hangs), missing-key configuration error. New opt-in
  **`live_ai`** marker (default addopts deselects `live` and `live_ai`); the live smoke reads the
  key from env or the repo-root `.env` and skips without it.
- Verification: `ruff` clean, `mypy app` strict clean, default suite green at every step; the live
  smoke awaits the real key (empty in `.env` at implementation time — ES-043 TD).

---

## ES-044

- Investigation Loop wired at runtime — the slice's "one agent decision loop wired at runtime"
  component: **concrete StateAssembler** (`ai/orchestration/assembler.py`, the first realization of
  the Workspace/Context Builder responsibility, planner-agent §4) assembles `InvestigationState`
  from the Investigation Service (single title-derived objective; strongest-finding confidence;
  bounded `kind: summary` history from the trace — the agent observes its own past; empty task
  fields); **`InvestigationRunner`** (`ai/orchestration/runner.py`) = assemble initial state + run
  loop, the invocation surface ADR-010 anticipated.
- **Run surface**: `POST /api/v1/investigations/{id}/run` (investigation router) — synchronous with
  a small configurable cycle budget (`RUN_CYCLE_BUDGET`, default 3; V-1 confirmed). Returns the
  `LoopOutcome` summary (`end`/`cycles`/`failure_code` + compact per-action results); the full
  explanation lives in the Trace. DI composition (`dependencies/services.py`): PlannerAgent over
  the Gemini provider (key via SecretProvider), live PlannerService as executor (graph =
  explicit-contract unavailable), InvestigationService as TraceSink, uuid/clock from the API
  boundary, all over the request's single transactional session.
- **planner-actions removed** (V-2 confirmed): the `/api/v1/planner` package, its schemas/tests and
  the transitional resource are gone from code and artifact; api-design bumped to **v1.3.0**
  (Investigation Run Resource replaces the Planner Action Resource section). The Planner Service
  remains the application-layer executor behind the loop; the ES-034 orchestration integration
  tests now drive it at the service seam and observe effects through the resource APIs.
- **Planner Agent prompt enriched** (implementation detail of the documented transformation
  boundary, planner-agent §6): the prompt now describes the exact JSON action vocabulary,
  instructs JSON-only output, carries evidence/finding ids and history, and tells the model not to
  repeat failed actions — a real provider can now actually play; unknown output still escalates.
  ES-011/035 contract tests unchanged and green.
- Presentation tests over scripted providers: completed run (summary + full trace kind sequence,
  also via the ES-045 HTTP read), provider failure → HTTP 200 `escalated` +
  `ai.llm_provider_error` with the investigation intact (ADR-013), budget exhaustion, contained
  downstream failure not stopping the run, 404 unknown investigation, 503 unbound runner.
- **Live proof with the real provider (invalid-credential path)**: `live_ai` test runs the real
  stack (live Postgres + real Google endpoint) with a deliberately invalid key — the run returns
  `escalated`/`ai.llm_provider_error` inside HTTP 200 and the investigation stays intact. The
  valid-key live run awaits the key (ES-043 TD).
- Verification: `ruff` clean, `mypy app` strict clean, default **317 passed** at the ES gate;
  artifact regenerated (planner paths out, run path in).

---

## ES-045

- Trace & Outcome read API implemented (closes the ES-039 "API exposure of Outcome and Trace"
  deferral): `GET /api/v1/investigations/{id}/trace` (append order; empty investigation → empty
  list, not an error) and `GET /api/v1/investigations/{id}/outcome` (0..1; missing outcome → the
  stable `investigation.outcome_not_found`, mapped 404 — distinct from an unknown investigation's
  `investigation.not_found`). Thin read-only controllers over the existing service operations
  (ADR-008); `TraceEntryResponse`/`OutcomeResponse` flat projections.
- The run test suite verifies the HTTP chain end to end: a completed run's trace read back over
  the ES-045 surface in the exact recorded kind order; the live_ai run test reads the persisted
  trace of a real run the same way.
- Verification: `ruff` clean, `mypy app` strict clean (143 files), default **323 passed** / 10
  deselected; live DB suite **7/7** green (reworked ES-042 live test drives the planner at the
  service seam); `live_ai` **1 passed** (invalid-credential escalation, real endpoint) + 2 skipped
  pending the key; `docs/api/openapi.json` regenerated (AC-15).

---

## ES-043/044/045 — Live AI verification addendum

- With the real `GOOGLE_API_KEY` supplied, the **`live_ai` suite is 3/3 green**: the Gemini smoke
  (one real `generate`), the full Investigation Loop run over the live stack (real model decisions;
  chronological decision/execution/outcome trace persisted in PostgreSQL and read back over the
  ES-045 surface) and the invalid-credential escalation. The default (323) and live-DB (7/7) suites
  stay green alongside.
- One robustness fix surfaced by the live run: the supplied `.env` value carried a **leading
  space** — an illegal HTTP header value (h11 `LocalProtocolError`). The adapter now trims the key
  at use (`.env`/`env_file` sources can carry stray whitespace; the ES-043 error mapping already
  contained the failure as `LLMProviderError`, proving the containment path), and the smoke-test
  loader normalizes too.

---

## ES-046

- The slice's real security chain implemented, replacing the deny-all defaults at runtime while
  keeping them as the fallback (ES-019/020 TD closed at dev grade; V-3 confirmed).
- **SharedTokenAuthenticator** (presentation, consuming the application `SecretProvider` port):
  `Authorization: Bearer <subject>:<token>` against the shared `DEV_AUTH_TOKEN` secret —
  constant-time comparison, credential material never in errors/logs, missing secret ⇒ 401 for
  everything (secure by default, identical to the unconfigured seam). Subject is caller-declared
  (dev-grade by design).
- **OperationContext (§6b) introduced with its first consumer**: subject + identity kind +
  correlation id, built at the boundary from the verified identity and the request context, stored
  on `request.state.operation_context` and carried explicitly into the decision.
  `AuthorizationRequest` extended additively (`correlation_id`, `investigation_id` from the matched
  route's path params) with a `for_context` factory — the ES-020 constructor contract and the audit
  middleware stayed untouched.
- **OwnerScopedAuthorizer (§6a)** — the first concrete policy (application layer, consulting the
  Investigation Service interface only, AC-07): investigation-scoped operations require ownership
  (foreign ⇒ 403 `authorization.denied`); unknown investigations defer to the owning service's 404;
  creation and the shared knowledge layers (memory/graph — §6a Shared Knowledge Boundary) stay open
  to authenticated identities; unrecognized operations are denied (least privilege).
- **Binding with graceful fallback**: the composition root binds both; the live authorizer yields
  `DenyAllAuthorizer` without a persistence registry, so every pre-policy test kept its exact
  behavior (401/403 unchanged). Audit already carries denied decisions with subject via the
  untouched ES-021 middleware (verified in the new e2e test with a recording recorder).
- Tests: 7 policy decision tests, 5 e2e security-chain tests (401 variants incl. credential
  hygiene, owner flow end to end, foreign 403 across surfaces, audit subject, shared-layer access),
  and a live full-chain test with **no dependency overrides** (real authn → owner policy → live
  Postgres: 401 / owner 200 / foreign 403). `.env.example` documents `DEV_AUTH_TOKEN`.
- Verification: `ruff` clean, `mypy app` strict clean (144 files), default **335 passed**, live
  suite **8/8** (new live auth-chain test included).

---

## ES-047

- The first vertical slice closed: the browser flow runs **without mocks** against the live stack
  (roadmap §7 satisfied; Delivery Record updated to "Delivered (live slice)", roadmap v1.2.0).
- **Token seam bound for real** (ES-023 TD): `setAuthTokenSource(getDevAuthCredential)` at the
  entry point; the credential (`subject:token`) is Session State (localStorage + in-memory mirror —
  Web Storage is unreliable on the test runtime) entered once through a header `DevTokenField`.
- **Same-origin by default**: `VITE_API_BASE_URL` default became empty (relative); the Vite dev
  server now proxies `/api` and `/health` to the local backend (mirroring the nginx reverse proxy),
  so no CORS surface exists in either mode. `frontend/.env` no longer bakes an absolute origin.
- **MSW removed from the app** (V-2 of the frontend world): `main.tsx` renders directly; the
  browser worker/handlers and the `msw` dependency are gone; `mocks/data.ts` stays as shared test
  fixtures (the page tests always mocked communication loaders directly).
- **AI Insights region goes live** (the ES-024 "awaiting exposure" note closes): trace list from
  `GET .../trace` through the server-state layer + the **Run investigation** interaction — outcome
  badge presents completed/escalated/exhausted with the stable `failure_code` (ADR-013 made
  user-visible); run errors render as region alerts, never break the app. The run request carries a
  budget-sized timeout (a 3-cycle Gemini run exceeds the 15s default — found in live verification).
- **Flow completers**: minimal create-investigation form on the landing page (owner = the
  authenticated dev subject) and a minimal attach-evidence form in the Evidence region — §2's
  "create → evidence → run → observe" flow interpreted as browser-complete (small scope decision
  over the §3 letter, recorded here). First mutations arrive through thin `useMutation` hooks with
  the centralized `invalidateInvestigationData` helper (ES-027 boundary preserved: the library is
  touched only in `state/`).
- Hand-written transitional DTOs (`communication/run.ts`, `communication/trace.ts` + create/attach
  inputs) per api-design §14a.
- **Live browser verification** (Vite dev + live backend + real Gemini + live Postgres, no
  overrides): dev credential entered → investigation created (owner alice) → evidence attached →
  run → **completed after 2 cycles** badge + the full decision/execution/outcome trace rendered in
  AI Insights — including the earlier run's `exhausted` trace with contained
  `FindNeighborsAction: failed` entries (the failure-isolation contract visible to the analyst).
  One fix from verification: the run timeout above.
- Verification: frontend lint 0 errors / `tsc -b` clean / **62 tests** / build green (fetch-boundary
  architecture test included); backend gates unchanged-green (335 / live 8/8 / live_ai 3/3).

---

## ES-048

- Neo4j made the real authoritative graph store (second slice, Part 1; ES-006 TD closed): concrete
  `Neo4jGraphRepository` over the async driver (Entity/Relationship CRUD, `list_relationships_for_entity`,
  and real variable-length `find_neighbors`), a versioned idempotent schema migration mechanism, and
  the runtime binding that takes the Graph API and the planner's graph action live.
- **Migration mechanism** (`neo4j/schema.py`, graph-service §11a): a single `(:SchemaVersion
  {id:'graph'})` node holds a **generic** integer version; ordered steps apply `CREATE CONSTRAINT/
  INDEX IF NOT EXISTS` (v1: `Entity.id` uniqueness + `REL.id` range index). Version-gated + idempotent
  primitives ⇒ re-running is a no-op; an empty graph migrates deterministically to head. Schema
  commands auto-commit (run outside a managed tx). Not run in the app lifespan (startup stays
  store-free); invoked by the live-test setup and the future seed utility.
- **Relationship modelling decision**: a single Neo4j type `REL` carries the open-string domain
  `type` as a **property**; entity `attributes` (a dict) is a JSON-string property, `aliases` a
  native string list; `created_at` round-trips through the driver's temporal type. This keeps the
  type vocabulary out of the graph structure — the exact shape that makes the vocabulary deferrable
  without reopening the migration mechanism (three deferral conditions confirmed; tracker TD).
- **CRUD** uses managed read/write transactions (automatic transient retry). Driver-level
  unavailability (`ServiceUnavailable`/`SessionExpired`/`OSError`) is mapped to the existing stable
  `GraphStoreUnavailableError` (`graph.store_unavailable`) — so the Planner Service still contains it
  as a failed execution result and the Graph API translates it to 503. Neo4j is a separate bounded
  context; no cross-store transaction with PostgreSQL (identifiers only, §8a).
- **Runtime binding** (`dependencies/services.py`): `get_graph_service` bound to the live adapter
  (Graph API 503 → real data / 404); the planner composition uses the real graph service, so
  `find_neighbors` returns real neighbours (contained failure only when Neo4j is unreachable).
  Registry gains `ping_neo4j`; `/health/ready` now probes and **reports** Neo4j
  (`neo4j: ok|unavailable|not_initialized`) but gates overall-ready on **PostgreSQL only** —
  documented deviation from the plan's exit criterion (graph degrades to contained failures; CI's
  live lane is Postgres-only). The unchanged `neo4j` readiness field prompted an `openapi.json`
  regeneration (readiness description) — AC-15.
- **Tests**: new `live_neo4j` marker (default `addopts` deselects it). `tests/live/test_neo4j_graph.py`
  (6 tests): idempotent bootstrap determinism, entity CRUD + reuse-by-identity + attributes/aliases
  round-trip, relationship CRUD + endpoint validation + incident listing, real multi-hop
  `find_neighbors` with `max_nodes` bound, the Graph API live over Neo4j (503 gone → 404 for unknown),
  and the planner returning real neighbours. Support (`neo4j_support.py`) reads `NEO4J_*` from the
  env (symmetric to the Postgres support). `test_live_api.py` reworked (graph is live: its readiness
  assertion is field-based, its graph-API-503 assertion removed; the graph-unavailable failure path
  kept via an explicit unavailable repo so the `live` lane stays Postgres-only). CI gains
  `backend-live-neo4j` (Neo4j service container); compose publishes `127.0.0.1:7687/7474` and relaxes
  Neo4j's min-password-length for local dev.
- **Live verification** (real Neo4j via compose): a startup issue surfaced and was handled — the
  dev `NEO4J_PASSWORD` (`1234`) is under Neo4j 5's 8-char minimum, so the dev compose now sets
  `NEO4J_dbms_security_auth__minimum__password__length=1` (dev only). Two Windows/host test-infra
  fixes: credentials/URI come from the env for both the tests and the app under test
  (`NEO4J_URI=bolt://127.0.0.1:7687` + `NEO4J_PASSWORD`), and the graph-API test opens/closes its
  driver within one event loop (proactor rejects cross-loop socket close).
- Verification: `ruff` clean, `mypy app` strict clean (147 files), default **335 passed** / 17
  deselected; **`live_neo4j` 6/6**; `live` (Postgres) **8/8** unchanged; `openapi.json` regenerated.

---

## ES-049

- ADR-012 §3 realized (second slice, Part 2 foundation; ES-007/009 TD embedding parts): the
  Memory Service's **application-owned embedding port** + the concrete **Gemini embedding adapter**
  (K-2), on one shared provider that both ES-050 (memory) and ES-051 (AI-side query) will consume.
- **Application port** (`app/application/memory/embedding.py`): `MemoryEmbedder` Protocol
  (`embed(text) -> tuple[float,...]`) + `MemoryEmbeddingError` (`memory.embedding_error`),
  provider-neutral (no AI import) — so the Memory Service never depends on the AI Runtime (AC-04).
- **Concrete AI provider** (`app/infrastructure/ai/gemini_embedding.py`): `GeminiEmbeddingProvider`
  realizes the AI Runtime `EmbeddingProvider` port over the Gemini `embedContent` REST API via httpx,
  mirroring the ES-043 LLM adapter — `asyncio.timeout` bound; transport/non-200/quota/malformed/
  empty-or-non-numeric-vector all mapped to `EmbeddingProviderError` (bounded, key-free); key via
  `SecretProvider` (`GOOGLE_API_KEY`), header-only + trimmed, missing key → `SecretNotFoundError` at
  construction; injectable transport for tests.
- **Bridge** (`app/infrastructure/ai/memory_embedding.py`): `EmbeddingMemoryAdapter` implements the
  memory port by delegating to the AI `EmbeddingProvider` and translating `EmbeddingProviderError` →
  `MemoryEmbeddingError` (ADR-012 §3 "may internally use the AI Runtime's provider-neutral port"; infra
  implements one layer's port while consuming another's). Same-signature protocols, but the bridge
  keeps the memory error contract clean.
- **Config** (`app/config/ai.py`): `GeminiEmbeddingSettings` (`GEMINI_EMBEDDING_` prefix; `model`
  default **`gemini-embedding-001`**, `timeout_seconds`) + `get_gemini_embedding_settings()`;
  `GeminiSettings` untouched. `.env.example` documents the embedding vars.
- **Model id correction from the live smoke**: the initial default `text-embedding-004` returned
  HTTP 404 (`not supported for embedContent`) — the adapter surfaced it cleanly as
  `EmbeddingProviderError` (error mapping proven). `ListModels` showed `gemini-embedding-001|-2`; the
  stable `gemini-embedding-001` is the default.
- **Tests**: 10 fake-transport contract tests (`tests/infrastructure/test_gemini_embedding.py`:
  success + key hygiene, 429/500/empty/missing/non-numeric/malformed/transport mappings, the
  execution bound, missing-key config error), 2 bridge delegation/translation tests
  (`test_memory_embedding_adapter.py`), and the opt-in `live_ai` embedding smoke
  (`test_gemini_embedding_smoke.py`).
- Additive only — no DI/lifespan/readiness/OpenAPI change; `live`/`live_neo4j` unaffected.
- Verification: `ruff` clean, `mypy app` strict clean (150 files), default **347 passed** / 18
  deselected; `live_ai` embedding smoke green against real Gemini (`gemini-embedding-001`). (The LLM
  smoke transiently hit a free-tier rate-limit during the back-to-back `live_ai` batch — surfaced as
  a clean `LLMProviderError` and re-passes in isolation; not an ES-049 regression.)

---

## ES-050

- ADR-012's core delivered (second slice, Part 2; closes ES-007's vector-store/sync TD): the
  transactional outbox, the idempotent embedding projector, the Qdrant collection and the background
  runner — MemoryItem writes now propagate asynchronously to real semantic embeddings in Qdrant.
- **Option B — `MemoryItem.content`** (owner decision): additive free-text field (default `""`)
  spread across domain (`content: str = ""`), Postgres (column via migration `0003`, mapper), and the
  memory API DTOs (create/update/response). The embeddable text is `content` (a blank content falls
  back to the type so a point always exists). Existing construction sites unaffected (default).
- **Transactional outbox** (migration `0003` `memory_outbox`; `outbox_orm.py`): `PostgresMemoryRepository.add`
  writes a `memory_outbox` intent **in the same session/transaction** as the memory row, so no request
  path writes to two stores (AC-14 by construction). `create`→add(v1), `update`(supersede)→add(v2)
  enqueue; `deprecate` (in-place `update`) does not (embed text unchanged). Application ports
  `OutboxRepository` (read/mark, `outbox.py`) and `MemoryVectorStore` (`vector_store.py`) keep the
  projector free of infrastructure imports.
- **Idempotent projector** (`app/application/memory/projector.py`, Memory-Service-layer-owned): drains
  pending records → reads the latest MemoryItem → embeds (`MemoryEmbedder`) → upserts to the vector
  store → marks processed; embed/store failure → `mark_failed` (record kept, MemoryItem untouched —
  "embedding failures never corrupt Memory Items"). Idempotence = the Qdrant point id is `UUID5(memory_id)`
  (`QdrantMemoryVectorStore`), so re-projection upserts the same single point.
- **Deterministic dimension**: `GeminiEmbeddingSettings.dimensions` (default 768) → the ES-049 adapter
  sends `outputDimensionality` → the Qdrant collection (`memory_embeddings`, Cosine) is created at that
  size.
- **Background runner** (`app/dependencies/projector.py`): lifespan-started, gated by
  `outbox_projector_enabled` (default on), builds the Gemini embedder (via SecretProvider; a missing
  key stops it cleanly without breaking startup) + the Qdrant store, polls `project_pending` on an
  interval, tolerates outages (log + retry), cancelled on shutdown. Tests disable it / call
  `project_pending` directly. Readiness gains a Qdrant probe + `qdrant` field (Postgres still gates).
- **Tests**: 5 projector unit tests (fake ports — embed/upsert/mark, failure isolation, idempotent
  re-projection, content-vs-type text, gone-item settle); new `live_qdrant` marker + suite
  (`test_memory_outbox_qdrant.py`, PostgreSQL + real Qdrant + **fake deterministic embedder**):
  two versions of one item → two outbox intents → one Qdrant point (idempotency), and embed-failure
  isolation. CI `backend-live-qdrant` job (Postgres + Qdrant service containers); compose publishes
  `127.0.0.1:6333`; existing live memory truncation lists gained `memory_outbox`; `openapi.json`
  regenerated (memory DTOs + readiness).
- **Not implemented (TD)**: embedding regeneration/versioning/GC, point deletion on Memory Item
  deletion, batch embedding, projector backoff/dead-letter, AC-14 mechanical enforcement, circuit
  breaker/scale-out. An end-to-end real-Gemini-embedding→Qdrant (dimension 768) path is exercised by
  the ES-053 demo, not a dedicated live_ai test here.
- Verification: `ruff` clean, `mypy app` strict clean (157 files), default **352 passed** / 20
  deselected; **`live_qdrant` 2/2**; regression `live` **8/8** + `live_neo4j` **6/6** green (Postgres
  migrated through `0003`, memory `content` round-trips); `openapi.json` regenerated.

---

## ES-051

- Live RAG retrieval delivered (second slice, Part 3; closes the ES-013 "concrete source-backed
  retrievers" + "live DI/lifecycle wiring" deferrals and the ES-049 "AI-side query embedding"
  consumer): the `Retriever` port has its first concrete implementation and the Retrieval Flow
  now runs at runtime inside the investigation run path.
- **CompositeRetriever** (`infrastructure/ai/retrieval.py`, infrastructure edge code implementing
  the AI-layer port — the ES-043/049 provider pattern): **semantic** = objectives embedded via the
  AI `EmbeddingProvider` (shared Gemini adapter) → `MemoryVectorStore.search` (new port operation)
  → matches mapped back to the **authoritative** Memory Items; **structured** = latest Memory Items
  of the investigation via the new `MemoryService.list_for_investigation`; **graph** = findings'
  related-entity neighbourhood via the Graph Service (1 hop + incident relationships); `external`
  deferred (Milestone C); `hybrid` expands to the organizational three. Per-strategy failure
  containment; deprecated memory filtered; dangling §8a references observable-and-skipped.
- **Vector-store read path**: `MemoryVectorMatch` + `search` on the application port; the Qdrant
  adapter queries by cosine similarity, returns () for an absent collection, and maps
  driver/transport failures to the new stable `memory.vector_store_unavailable` (the
  `graph.store_unavailable` pattern).
- **Memory listing**: `MemoryRepository.list_for_investigation` + service operation — latest
  version per item, investigation-scoped, deterministic `(created_at, id)` order (needed by the
  structured strategy now, by the ES-052 REST surface next).
- **Run-path consumption**: `InvestigationState.knowledge` (additive), the planner prompt carries
  `retrieved_knowledge`, `InvestigationStateAssembler.next_state` preserves knowledge across
  cycles, and `InvestigationRunner` executes the Retrieval Flow **once per run** (owner decision)
  with contained failure (run proceeds knowledge-less). DI composes MemoryAgent (shared Gemini
  LLM), RagPipeline over the CompositeRetriever, and the RetrievalFlow with the Investigation
  Service as trace sink — one RETRIEVAL trace entry per successful retrieval (ES-039 contract).
- **Tests**: 9 CompositeRetriever unit tests (fakes + in-memory services), 5 runner retrieval
  tests, assembler knowledge-preservation test, planner prompt knowledge test (ai_validation);
  live: `live` gains the list_for_investigation round-trip (9/9), `live_qdrant` gains the
  projected-then-retrieved semantic round-trip with a directional fake embedder (3/3),
  `live_neo4j` regression green (6/6).
- Verification: `ruff` clean, `mypy app` strict clean (158 files), default **368 passed** / 22
  deselected; live suites 9/9 + 3/3 + 6/6; **`live_ai` 4/4** — the full live run now executes
  through the retrieval-wired composition (real Memory Agent decision, real query embedding,
  real Qdrant search) with the chronological trace intact. No REST contract change
  (`openapi.json` freshness test green, AC-15).

---

## ES-052

- Investigation-scoped Memory surface delivered (second slice, Part 4; closes the ES-025 "Memory
  Region placeholder / no list-memory-by-investigation endpoint" deferral): the workspace Memory
  region is live and the second slice is user-visible end to end.
- **Backend**: `GET /api/v1/memory?investigation_id=<id>` over the ES-051
  `MemoryService.list_for_investigation` (latest version per item, deterministic order, unknown
  investigation => empty list — §8a structural reference). Thin controller reusing the
  envelope/error foundation; `Query(min_length=1)` transport validation; the shared-knowledge
  policy rule covers the operation unchanged. `openapi.json` regenerated (AC-15).
- **Frontend**: `communication/memory.ts` (transitional DTO + `MemoryItemViewModel` +
  `loadInvestigationMemory`), `memoryQuery` + `invalidateMemory` in the `state/query.ts` boundary
  (memory joins `invalidateInvestigationData`, so runs/mutations refresh the region),
  `useInvestigationMemory` hook, and `MemorySection` (type, status badge, content, version +
  confidence; loading/error/empty states) replacing the placeholder in the workspace page.
- **Test-infra fix**: the memory API test client rebuilt its id generator per request (a defaulted
  lambda), so successive creates collided on "id-1" — the client now captures one shared counter
  (the ES-034 closure-capture note strikes again).
- **Tests**: 3 new memory API tests (latest-version listing, unknown-investigation empty,
  missing-parameter 422); MemorySection component tests (items render with type/status/confidence,
  empty state, contained load failure + retry); the presentation memory double gained
  `list_for_investigation`.
- Verification: `ruff` clean, `mypy app` strict clean (158 files), backend default **371 passed** /
  22 deselected; frontend lint/`tsc -b` clean, **65 tests**, build green. Live browser proof
  (headless Chrome via CDP against Vite dev + live backend + live stores, no mocks): dev credential
  committed, workspace loads, the Memory region renders two live Memory Items with status badges
  and confidence — screenshot captured. (The Claude preview tunnel strips `Authorization` headers,
  so the in-pane flow 401s; the CDP run is the real-browser verification path.)

---

## ES-053

- Seed utility & second-slice demo delivered (Milestone A closed): `backend/scripts/seed_demo.py`
  produces a demonstrable environment on one command — PostgreSQL migrated to head, the Neo4j
  graph schema bootstrapped (the utility is the ES-048 mechanism's documented second invoker),
  and a consistent demo dataset seeded **through the services**: one investigation, 2 evidence
  items, 2 confirmed findings (related entities), 3 graph entities + 2 relationships, 3
  content-rich Memory Items.
- **End-to-end real-embedding path proven** (the check ES-050 delegated here): the seeded Memory
  Items' outbox records were projected into Qdrant with **real Gemini embeddings**
  (`gemini-embedding-001`, 768-dim) — 6 points on the live store, including the previous run's
  pending backlog (at-least-once outbox semantics visible in practice).
- **Demo walkthrough (headless Chrome over CDP, live stack, no mocks)**: dev credential → the
  seeded workspace renders every region live — overview, confirmed findings, evidence, derived
  timeline, entity-seeded graph chips (`demo-host-1/ip/domain`), and the ES-052 Memory region
  with the three knowledge items; "Run investigation" exercised the run surface (see the TD
  entry: the provider's multi-hour 503 window made the run end in the documented
  degrade-to-escalation, stable code visible in the outcome badge — the happy path stands proven
  by `live_ai` 4/4 over the same composition).
- The walkthrough instructions live in the script docstring + its final output (self-documenting;
  workdocs stays limited to its two committed files).
- Bookkeeping: roadmap **v1.3.0** — Delivery Record rows for the second slice flipped to
  Delivered (Neo4j+Qdrant/ADR-012, live RAG retrieval, workspace Memory surface); README status
  table gains the ES-051/052/053 rows; Jira SEN-4/SEN-20 closable.
- Verification: `ruff` clean (seed script included), `mypy app` strict clean (158 files), default
  **371 passed** / 22 deselected; seed run output verified against live stores; screenshotted
  browser walkthrough over Vite dev + local uvicorn + compose data tier.

---

## ES-054

- Second concrete LLM provider delivered (owner decision, triggered by multi-hour Gemini
  `generateContent` 503 windows): `infrastructure/ai/nvidia.py` realizes the provider-neutral
  `LLMProvider` port over the NVIDIA NIM OpenAI-compatible `/v1/chat/completions` API via httpx —
  default model **minimaxai/minimax-m3** (`NVIDIA_MODEL` configurable). ADR-013 contract mirrored
  from ES-043: bounded execution (default 90s — reasoning-model headroom), total error mapping,
  key via SecretProvider (`NVIDIA_API_KEY`, Authorization-header-only, trimmed, never logged).
  Reasoning normalization is adapter-owned: `<think>…</think>` blocks are stripped (the port's
  `text` is the answer); reasoning-only responses map to `LLMProviderError`.
- **Provider selection**: `LLM_PROVIDER=gemini|nvidia` (closed enum, `config/ai.py`), consumed by
  the composition root's `_llm_provider()`; the planner and memory agents share the selected
  instance. Embedding stays on Gemini (Qdrant 768-dim binding, ES-050). `.env` now selects nvidia.
- **Memory-agent prompt enriched** (the ES-044 planner precedent applied to the second agent): the
  minimal "respond as JSON" prompt made every real provider fail strategy selection (unrecognized
  → empty plan → retrieval silently skipped — masked until now by scripted-response tests and the
  contained failure path). The prompt now names the exact JSON shape and the strategy vocabulary;
  ES-012/035 contract tests unchanged and green.
- **Dev auto sign-in**: `VITE_DEV_AUTH_CREDENTIAL` in the gitignored `frontend/.env.local` signs
  the sole developer in on dev-server builds (`devAuth` falls back to it when nothing is stored;
  an explicitly entered credential wins; production builds never carry the variable; vitest
  force-empties it so the real `.env.local` cannot leak into tests). Backend security chain
  (ES-046) untouched.
- **Tests**: 11 NVIDIA contract tests (`httpx.MockTransport`: happy path + think-strip +
  reasoning-only + 429/503/choice-less/content-less/malformed/transport/bound/key hygiene +
  missing-key configuration error), 2 devAuth fallback tests. Backend default **382 passed** /
  22 deselected; `ruff` clean; `mypy app` strict clean (159 files); frontend **67 tests** green.
- **Live proof (headless Chrome, no credential injected, live stack)**: auto sign-in renders
  "Signed in: koray"; "Run investigation" on the seeded demo completes — trace shows
  `retrieval: retrieved 15 item(s) via ['semantic','graph','structured']` (MiniMax-M3 strategy
  selection → Gemini query embedding → Qdrant/graph/memory retrieval) →
  `planner_decision: ControlAction` → `action_execution: completed` → `loop_outcome: completed
  after 1 cycle(s)` — the full Milestone A happy path, user-visible with the new provider.
- TD: no cross-provider fallback/retry chain (Milestone G); `live_ai` lane not yet
  provider-parameterized; the compose backend image predates ES-051+ (rebuild when the container
  flow is next needed).

---

## ES-055

- Decision Engine delivered (Milestone B opener; planner-agent §7 "Investigation Complete? →
  Decision Engine" realized): `app/ai/decision/engine.py` synthesizes the investigation's
  **confirmed** (validated/accepted) findings into one `InvestigationOutcome`
  (status `SYNTHESIZED`, 0..1) over the selected LLM provider — the ES-045 read-only outcome
  surface gains its documented writer. Not an agent (agent-architecture §6): an Intelligence
  Layer component; AI → Application one way (findings/outcome via the Investigation Service).
- **Synthesis, never invention**: contributing-finding references outside the confirmed set are
  discarded (absent selection → all confirmed findings, deterministic completion); confidence
  clamps to [0,1]; conflict/open-question lists are string-filtered and bounded (10); a malformed
  synthesis raises `DecisionEngineError` (`ai.decision_engine_error`) — no safe fallback
  recommendation exists, so nothing is persisted. Skip conditions return `None` without a
  provider call: outcome already exists (re-runs stay cheap) or no confirmed finding (an outcome
  must stay finding-backed).
- **Loop integration** (additive `synthesizer` port, `OutcomeSynthesizer`): on a COMPLETED
  control action the loop synthesizes best-effort — a produced outcome is traced as the new
  additive `TraceEntryKind.OUTCOME_SYNTHESIS` (actor `decision-engine`, reference = outcome id,
  confidence + conflict/question counts in the summary, ordered before the terminal
  LOOP_OUTCOME); a failed synthesis is traced with its stable code and never breaks the
  completed run; a skipped synthesis is log-only (no trace noise on empty investigations);
  escalated/exhausted runs never synthesize.
- **Frontend**: AI Insights gains the synthesized-outcome panel (recommendation, confidence %,
  conflicts, open questions — advisory presentation); `communication/outcome.ts` maps the 0..1
  semantics (`investigation.outcome_not_found` → null, a normal state); `outcomeQuery` +
  `invalidateOutcome` join the `state/query.ts` boundary and the post-run invalidation family.
- **Tests**: 8 engine unit tests, 5 loop synthesis tests, 3 behavioral validation tests
  (adversarial matrix → never a fabricated outcome; provenance; repeatability), 1 end-to-end
  presentation test (completed run → HTTP outcome read + synthesis trace), 2 frontend panel
  tests. Backend default **399 passed** / 22 deselected; `ruff` clean; `mypy app` strict clean
  (161 files); frontend **69 tests** + 4-gate green. No REST contract change (openapi freshness
  green).

---

## ES-056

- Validation Agent delivered (Milestone B, part 2; agent-architecture §6): the typed
  `validation-agent` assesses the investigation's findings against their supporting evidence over
  the selected LLM provider and produces one `ValidationAssessment` — per-issue vocabulary exactly
  the documented four distinctions (factual_inconsistency, missing_evidence,
  conflicting_observations, unsupported_conclusion), issues bounded (10), unknown kinds ignored,
  unknown finding references kept as observations but never attributed.
- **Composition**: `ValidationFlow` (agent through the Agent Runtime — single execution path,
  ADR-013) over the assembler's new `assemble_validation_context` (findings + evidence snapshots;
  `None` = nothing to validate). The loop's COMPLETE branch runs validation **before** synthesis
  (best-effort; traced as VALIDATION with counts + the agent's summary; a failure is traced with
  its stable code and synthesis proceeds without the assessment). The assessment is the Decision
  Engine's documented input — folded into the synthesis prompt.
- **Tests**: 8 agent/flow unit tests, 3 loop integration tests (validated-then-synthesized
  ordering, contained failure, escalated runs never validate), 4 behavioral validation tests
  (adversarial matrix → never a clean bill; partial recognition; provenance; repeatability).
- Verification: part of the Milestone B gate — `ruff` clean, `mypy app` strict clean, backend
  default **424 passed** / 22 deselected.

---

## ES-057

- Graph Analysis Agent delivered (Milestone B close; agent-architecture §6): the typed
  `graph-analysis-agent` reasons over the finding-seeded entity neighbourhood (assembler's new
  `assemble_graph_context`: seeds from findings' related entities, 1-hop neighbours + incident
  relationships, dangling §8a references skipped) and produces one `GraphAnalysis` — observations
  in the documented vocabulary (attack_path, lateral_movement, correlation, anomaly) with
  entity provenance bound to the snapshot.
- **Composition**: `GraphAnalysisFlow` (agent through the Agent Runtime) records its own
  GRAPH_ANALYSIS trace entry (RetrievalFlow pattern); the runner runs it once per run after
  retrieval and appends the observations to the planner-visible knowledge as `[graph-analysis]`
  lines (bounded 300 chars) — contained failure, the run proceeds unenriched.
- **Tests**: 10 agent/assembler/flow/runner tests (typed transformation + filtering, prompt
  provenance, malformed raises, precondition, finding-seeded assembly, graph-less/seed-less
  skips, flow tracing, runner enrichment + containment).
- **Milestone B closed** — live demo (headless Chrome, auto sign-in, real MiniMax-M3 over the
  seeded investigation): one completed run produced the full seven-kind trace — retrieval (15
  items) → graph_analysis (3 entities, 3 observations) → planner_decision → action_execution →
  validation (2 findings, 0 issues) → outcome_synthesis (confidence 0.85, 2 conflicts, 5 open
  questions) → loop_outcome — and the workspace rendered the synthesized-outcome panel
  (recommendation + conflicts + open questions). Notably the engine correctly classified the
  seed's duplicate memories as redundancy rather than conflicting evidence.
- Verification: `ruff` clean, `mypy app` strict clean (169 files), backend default **424 passed**
  / 22 deselected (+25 across ES-056/057); frontend unchanged since the ES-055 gate (**69
  tests**); no REST contract change (openapi freshness green). Delivery Record updated to
  Delivered for the initial specialized-agent set; Timeline/Report agents remain deferred
  (backlog), Threat Intelligence Agent belongs to Milestone C.


---

## ES-058

- External Knowledge layer turned on (Milestone C opener; the ES-051 external deferral closed):
  the EXTERNAL retrieval strategy now executes through the provider-neutral
  `ExternalKnowledgeProvider` port (ES-039) against two concrete adapters — infrastructure edge
  code implementing an AI-layer port, the ES-043/049/051 pattern:
  - **`AttackCatalogProvider`** (`app/infrastructure/ai/attack_catalog.py`) — a bundled,
    revisioned, curated MITRE ATT&CK technique subset (`attack_catalog.json`, ~21 techniques
    across the kill chain), case-insensitive whole-word keyword matching, hit-count ranking,
    result bound 5, bounded relevance confidence (0.4 + 0.1/hit, ceiling 0.9). Deterministic,
    offline, CI-able; a broken bundled catalog surfaces eagerly at construction. Wheel packaging
    verified (hatchling includes the JSON).
  - **`NvdCveProvider`** (`app/infrastructure/ai/nvd.py`) — live NVD REST API 2.0 over httpx
    (no vendor SDK; ES-054 contract pattern: `asyncio.timeout` bound, total error mapping to
    `ExternalKnowledgeError`, bounded key-free error detail). Explicit CVE ids in the query
    resolve via `cveId`; otherwise a 256-char-bounded `keywordSearch`. `NVD_API_KEY` optional
    by NVD's own contract (keyless degrade, key only ever the `apiKey` header); malformed items
    inside a valid payload are skipped, never fatal; fixed neutral confidence 0.5.
- **Retriever integration**: `CompositeRetriever` gained an additive `external` tuple; the
  EXTERNAL strategy queries every composed provider with the investigation objectives,
  containing failures **per provider**; items keep their origin (`mitre-attack:T1071`,
  `nvd:CVE-...`) so external knowledge stays distinguishable (rag §17). External items reach
  the planner-visible knowledge lines and the RETRIEVAL trace entry through the ES-051 path
  unchanged — no REST change (AC-15 untouched).
- **Configuration**: `EXTERNAL_KNOWLEDGE_PROVIDERS` (closed vocabulary `attack,nvd`, default
  both, empty opts out — unknown tokens rejected at settings load) + `NVD_TIMEOUT_SECONDS` /
  `NVD_RESULTS_LIMIT`; composition root builds the selected adapters into the retriever;
  `.env.example` documents all of it. Memory Agent prompt: the external strategy's
  "(not yet available)" note lifted.
- **Tests (+26)**: 9 ATT&CK catalog tests (bundled-catalog load + keyword semantics + ranking/
  bounds + confidence growth + eager malformed/missing failures), 11 NVD contract tests over
  `httpx.MockTransport` (mapping + key hygiene + keyless degrade + cveId path + query/result
  bounds + item-skip + 403/malformed/missing-list/transport/timeout), 3 retriever external
  tests (provenance mapping, per-provider containment, no-providers no-op), 4 settings tests
  (dedup/order, case, empty opt-out, unknown rejection). Functional sanity: the seed demo
  objective ("beaconing from HOST-1") retrieves T1071 Application Layer Protocol.
- Verification: `ruff` clean; `mypy app` strict clean (171 files); backend default **450
  passed** / 22 deselected; frontend untouched since the ES-055 gate; openapi freshness green.
- TD: NVD keyword search rarely matches prose objectives (ES-059's focused queries are the
  consumer); no external-call retry/backoff (Milestone G); catalog refresh cadence unowned.


---

## ES-060

- Evidence Payload Store delivered (Milestone D opener): raw evidence payloads now live in a
  content-addressed store behind documented governance — **RFC-001** (first exercised RFC under
  ADR-014: amending ADR-003's ownership map crosses threshold (a)) and **ADR-015** (the accepted
  decision). Database-architecture §8b's "requires its own decision" precondition is satisfied;
  §8b and api-design gained realization notes + version-history rows; the ADR index lists 015.
- **Application**: `EvidencePayloadStore` port (minimal: idempotent `put`, `get` with `None` for
  unresolvable addresses, `exists`) + application-owned addressing (`payload_address` =
  `sha256:<64 hex>`; deterministic derivation, never id generation). Investigation Service
  mediates every access (§8b rule 3): `store_evidence_payload` (require investigation → compute
  address → put; object-store write only), `get_evidence_payload` (evidence-anchored fetch +
  **hash verification on read**; opaque-integrity evidence → 404 payload_not_found; dangling
  address → observable 404; mismatch → 409 payload_integrity), attach-time validation for
  address-shaped (`sha256:`) integrity values only (broken reference → 422 payload_missing;
  opaque interim values and store-less compositions keep prior behavior exactly).
- **Infrastructure**: `FilesystemEvidencePayloadStore` (dev-grade first adapter, ADR-015 §4):
  `<root>/sha256/<xx>/<hex>` layout, atomic temp+replace writes, idempotent puts, strict
  address validation before any path construction (= path-traversal guard), OSError →
  `evidence_payload_store_unavailable` 503. Config `EVIDENCE_PAYLOAD_ROOT` /
  `EVIDENCE_PAYLOAD_MAX_BYTES`; compose gains the `evidence-payloads` volume mounted at
  `/data/evidence-payloads`; dev root `backend/var/` gitignored; `.env.example` documents both.
- **REST (AC-15 regenerated)**: `POST /investigations/{id}/evidence/payloads`
  (`application/octet-stream` → 201 enveloped `{address, size_bytes}`; Content-Length precheck
  + post-read bound → 413 `api.payload_too_large`; empty body → 422 `api.invalid_payload`) and
  `GET /investigations/{id}/evidence/{evidenceId}/payload` (verified byte stream,
  Content-Disposition with sanitized filename; cross-investigation access → 404). Owner scoping
  is inherited automatically — both routes carry the `investigation_id` path param the
  ES-046 policy keys on. The envelope stays scoped to structured JSON resources (api-design
  1.4.0 note).
- **Tests (+29)**: 15 service-op tests (addressing determinism/malformed matrix, store/require/
  unavailable, verified roundtrip, inline→404, dangling→404, corrupt→409, attach validation
  matrix incl. store-less no-op), 6 filesystem adapter tests (roundtrip, idempotence, layout,
  unknown→None, hostile addresses never touch the filesystem, malformed put → ValueError),
  9 presentation tests (upload→attach→download roundtrip, idempotent re-upload + size, 404
  unknown investigation, 422 empty, 413 over bound, 422 unstored address, 404 inline download,
  409 corrupted download, 404 cross-investigation). In-memory payload store double added to
  `tests/support`.
- Verification: `ruff` clean; `mypy app` strict clean (174 files); backend default **479
  passed** / 22 deselected; `openapi.json` regenerated and freshness green; frontend untouched
  (ES-061 owns the workspace surface).
- Milestone C note: ES-059 (Threat Intelligence Agent) stays reserved — C paused by owner
  decision in favor of D on 2026-07-17.


---

## ES-059

- Threat Intelligence Agent delivered (Milestone C close; agent-architecture §6): the typed
  `threat-intel-agent` correlates the investigation's facts with already-retrieved external
  intelligence over the selected LLM provider and produces one `ThreatIntelReport` —
  observations in the documented vocabulary (ioc_enrichment, cve_correlation, attack_mapping,
  threat_actor; closed enum, unknown kinds ignored, bounded 10) with provenance bound to the
  assembled intelligence: references the platform never retrieved are discarded (the
  observation survives), so external claims are always traceable to a real lookup.
- **Composition**: `ThreatIntelFlow` (agent through the Agent Runtime, ADR-013) derives
  **focused queries** — the objectives plus each finding-named entity's display name (the
  assembler's new `assemble_threat_intel_seed`; entity-less seeds valid) — runs them over the
  ES-058 providers with per-provider containment, dedupes by (source, reference) capped at 10,
  and skips quietly (`None`, no trace noise) when nothing external applies. A produced report
  is traced as the additive `TraceEntryKind.THREAT_INTEL` (actor `threat-intel-agent`,
  correlated-items + observation counts + the agent's summary). The runner runs the flow once
  per run after graph analysis; observations join the planner-visible knowledge as
  `[threat-intel]` lines (bounded 300 chars); a failed correlation is contained.
- **Frontend**: no code change needed — the workspace trace region renders kinds generically;
  a new AiInsightsSection test pins the `threat_intel` entry's workspace visibility.
- **Tests (+19)**: 14 agent/assembler/flow/runner tests (typed transformation + provenance
  filtering, prompt derivation, malformed/summary-less raises, precondition, seed assembly
  with/without graph, focused queries + tracing, quiet skip, per-provider containment, origin
  dedupe, agent-failure raise, runner enrichment + containment), 4 behavioral validation tests
  (adversarial matrix → never a silent report; fabricated references never attributed;
  reasoning derives from context; repeatability), 1 frontend trace-visibility test.
- **Milestone C closed — live proof** (host backend over the compose data stack, real
  MiniMax-M3 + real Gemini embeddings + real NVD HTTP calls): the seeded investigation's run
  produced `retrieval: 18 item(s) via ['semantic','graph','structured','external','hybrid']`
  (ES-058 live) → `graph_analysis` → **`threat_intel: correlated 1 external item(s), 1
  observation(s): "Beaconing from HOST-1 to 203.0.113.7 over evil-cdn.example is consistent
  with [T1071]..."`** → `planner_decision` → `action_execution` → `validation` →
  `loop_outcome` — the full enrichment chain user-visible in the trace. First attempt showed
  the containment path live (provider timeout at the 90s bound → run completed unenriched);
  the demo run used `NVIDIA_TIMEOUT_SECONDS=180` (see TD).
- Verification: `ruff` clean; `mypy app` strict clean (178 files); backend default **497
  passed** / 22 deselected; frontend 4-gate green (**70 tests**); no REST change (trace kind
  travels as the existing string field — openapi freshness green). Delivery Record 1.5.0 +
  README status rows updated; Jira SEN milestone close is the owner's step (no Atlassian
  access from this session).


---

## ES-061

- Workspace evidence payload surface delivered (Milestone D close): the analyst uploads a raw
  evidence file from the workspace Evidence region and downloads a stored payload back,
  verified — the user-visible leg of ADR-015/§8b.
- **Communication boundary**: `apiClient` gained `postBinary` (octet-stream body, JSON envelope
  unwrapped) and `getBlob` (raw byte-stream response, JSON error envelope on failure), both
  through the shared auth-header + timeout + unreachable-mapping discipline (extracted `send` /
  `errorFrom` helpers so `request` stays identical). `investigations.ts` adds
  `uploadEvidencePayload` (→ `{address, size_bytes}`) and `downloadEvidencePayload` (→ Blob).
  Payloads never become JSON documents (api-design §8).
- **Two-step upload = the ES-060 shape**: `useUploadEvidencePayload` uploads the file bytes then
  attaches evidence referencing the returned content address as its integrity value, the file
  name as the normalized content label — two separate single-store operations (AC-14). Download
  goes through the authenticated boundary (`useDownloadEvidencePayload`: fetch Blob → object-URL
  → anchor click; a bearer-carrying `<a href>` is impossible, and the preview tunnel strips
  Authorization anyway). Both invalidate/read via the existing `state/query.ts` server-state.
- **View model**: `EvidenceViewModel.downloadable` derived from the `sha256:` integrity prefix
  (address-shaped = has a payload; opaque interim values do not). `EvidenceCard` restructured to
  a wrapper `div` (selection button + optional sibling download button — no nested interactive
  elements) exposing "Download payload" only on downloadable evidence.
- **Tests (+5)**: workspace `downloadable` derivation (address vs opaque); EvidenceSection —
  download control appears only on downloadable evidence, upload calls upload-then-attach with
  the returned address, download routes through the authenticated boundary. Page test view
  models carry the new field.
- **Milestone D closed — live proof** (host backend over the compose data stack): the exact UI
  sequence over the seeded investigation — `POST …/evidence/payloads` (raw octet-stream) → 201
  `{address: sha256:f15c4b89…, size_bytes: 65}` → `POST …/evidence` with the address as
  integrity → 201 (downloadable) → `GET …/evidence/{id}/payload` → 200 octet-stream,
  Content-Disposition attachment, **bytes byte-for-byte equal to the original**. Error contract
  live too: attach of an unstored address → 422 `evidence_payload_missing`; a 10 MiB+1 upload →
  413 `api.payload_too_large`. (Docker Desktop had to be restarted after a host sleep/wake —
  environment gotcha #4; the data profile recovered on relaunch.)
- Verification: backend `ruff`/`mypy` strict (178 files)/`pytest` **497 passed** unchanged;
  frontend 4-gate green (**74 tests**, +5); no REST contract change beyond ES-060 (openapi
  freshness green). NVIDIA default execution bound raised 90→180s (the ES-059 demo-proven value;
  the plan's 40 rpm limit is never approached — per-call latency is the constraint), `.env.example`
  updated. Delivery Record 1.6.0 + README rows updated; Jira SEN Milestone D close is the owner's step.


---

## ES-062

- Production identity provider delivered (Milestone E opener): the dev-grade shared token gains
  a production sibling — `JwtAuthenticator` (`app/presentation/api/jwt_authenticator.py`) behind
  the existing `Authenticator` port, selected by `AUTH_PROVIDER=dev|jwt` (default `dev`, so the
  platform is unchanged at rest). Verifies HS256-signed bearer JWTs over the standard library
  (no vendor SDK): fixed algorithm (rejects `alg:none`/RS confusion before signature check),
  constant-time HMAC compare, required `exp` + optional `nbf`/`iss`/`aud`, `sub`→subject,
  `kind`→identity kind; signing secret via SecretProvider (`AUTH_JWT_SECRET`), never logged.
- **Verifier, not issuer**: token issuance belongs to the external IdP (§4). A dev utility
  (`scripts/mint_dev_jwt.py`) + `tests/support/jwt.py` stand in for it; `app` grows no issuance
  surface.
- **owner==subject on create** (ES-047 TD closed): the create endpoint derives owner from the
  authenticated subject (`require_identity`), not the request body; `owner` removed from
  `InvestigationCreateRequest` and the frontend create input (HomePage form + `InvestigationCreateInput`);
  openapi regenerated. Auth-bypassing tests gained a shared `override_identity` seam
  (`tests/support/auth.py`).
- **WWW-Authenticate: Bearer** now accompanies every 401 (RFC 7235), set centrally in the
  exception handler.
- **Config**: `app/config/auth.py` (`AuthProviderChoice`, `AuthSelectionSettings`, `JwtSettings`);
  `.env.example` documents `AUTH_PROVIDER` and the `AUTH_JWT_*` block; DI `live_authenticator`
  selects the adapter.
- **Live proof** (host backend, `AUTH_PROVIDER=jwt`, compose data stack, tokens minted via the
  utility): no token → 401 `WWW-Authenticate: Bearer`; alice POST /investigations (no body owner)
  → 201 owner=alice; alice GET → 200; bob (foreign) → 403 `authorization.denied`; expired token →
  401 + challenge. The full production-identity chain — authenticate → per-subject identity →
  owner==subject → owner-scoped authorization — verified end to end.
- Verification: `ruff` clean; `mypy app` strict clean (180 files); backend default **519 passed**
  / 22 deselected (+22); frontend 4-gate green (**74 tests**); openapi freshness green. Two
  release-gate items closed (production IdP, owner==subject). TD carried: HS256/shared-secret
  (asymmetric/JWKS + refresh rotation deferred), two-sessions-per-request owner-scope refactor
  (ES-046) still open; multi-tenancy is ES-063 (Milestone E close).


---

## ES-063

- Multi-tenancy delivered (Milestone E close): investigations are isolated by tenant, not only
  by owner. Governance first — **RFC-002** (second exercised RFC; changes domain ownership/scoping
  → ADR-014 threshold c) + **ADR-016** (amends ADR-003 with an Investigation scope attribute);
  §6a realization note + ADR index updated.
- **Domain**: `Investigation.tenant: TenantId` (new typed scope key in `app/domain/identifiers.py`,
  exported via `app/domain/__init__.py`), caller-supplied from the authenticated identity.
- **Identity → policy flow** (all additive, defaults to `DEFAULT_TENANT="default"` defined in the
  application authorization layer): `AuthenticatedIdentity.tenant` (JWT `tenant` claim or default;
  dev authenticator → default) → `OperationContext.tenant` → `AuthorizationRequest.tenant` →
  `OwnerScopedAuthorizer` requires `identity.tenant == investigation.tenant` **and** the owner
  rule (tenant isolation is an added conjunct — cross-tenant → 403 before the owner check).
- **Create derives tenant + owner from the identity** (extends ES-062 owner==subject); a client
  cannot place an investigation in a foreign tenant. `InvestigationResponse` exposes `tenant`;
  create request does not take it (openapi regen).
- **Persistence**: `investigation.tenant` column (ORM + mapper); Alembic **0004** adds it NOT NULL
  `server_default='default'`, backfilling existing rows (the seed stays default-tenant reachable).
  Migration applied live (0003→0004).
- **Frontend**: `InvestigationDto`/summary view model carry `tenant`; workspace Overview +
  dashboard Summary show a Tenant field.
- **Scope boundary (RFC-002)**: shared knowledge layers (Memory/Graph) stay open — a per-tenant
  organizational-knowledge model and a managed Tenant entity/membership are documented follow-ups,
  not decided here.
- **Tests (+6 backend)**: foreign-tenant-denied-even-for-owner, matching tenant+owner permitted,
  `for_context` tenant, JWT tenant-claim + default, e2e cross-tenant isolation; frontend tenant
  assertions in the dashboard/summary tests.
- **Live proof** (host backend, `AUTH_PROVIDER=jwt`, compose data stack): alice@acme POST → 201
  owner=alice tenant=acme; alice@acme GET → 200; **alice@other (same subject, foreign tenant) →
  403 `authorization.denied`**; migration-backfilled seed → 200 for koray@default. Milestone E
  closed — production identity (ES-062) + tenant isolation (ES-063) complete.
- Verification: `ruff` clean; `mypy app` strict clean (180 files); backend default **525 passed**
  / 22 deselected; frontend 4-gate green (**74 tests**); openapi freshness green. Jira SEN
  Milestone E close is the owner's step.

## UI-R1 (ad-hoc, 2026-07-19): SOC-console frontend redesign

- **Scope**: full visual redesign of the frontend (user request; no ES). No behavior, routing,
  state, or API change — presentation layer only. All visible text, roles, aria attributes and
  test ids preserved; the 74-test frontend suite is unchanged except one accessible-name fix
  (`aria-label="SentinelAI"` on the split-styled Home h1).
- **Design system** (`src/index.css`, Tailwind 4 `@theme`): "SOC console" theme — dark default
  (near-black navy canvas, teal `--color-accent`, violet `--color-ai` for AI surfaces, semantic
  ok/warn/danger/info), full light-theme variable override via existing `data-theme` switch
  (ES-027 session state untouched). Typography: Space Grotesk Variable (UI) + JetBrains Mono
  Variable (data/micro-labels), self-hosted via `@fontsource-variable` (2 new deps, bundled by
  Vite — no runtime font CDN).
- **Component classes**: `.panel` (corner-bracket framing, hover glow), `.panel-title`, `.card`
  (+selected/highlighted), `.btn`/`.btn-primary` (hover light sweep)/`.btn-ghost`/`.btn-link`,
  `.input`, `.file-input`, `.status-dot` (sonar pulse), `.meter` (animated confidence fill +
  sheen), `.shimmer` skeletons, `.stagger`/`.fade-up` entrances, `.edge-flow` (animated directed
  graph edges), `.ambient` (fixed blueprint grid + drifting glows), frosted `.app-header` with
  radar-sweep underline. `prefers-reduced-motion` disables all animation.
- **Surfaces restyled**: MainLayout (sticky glass header, brand mark, status footer), Home hero,
  dashboard + workspace pages (breadcrumb headers, id chips, shimmer skeletons, danger-toned
  error panels), all region shells, finding/evidence cards, timeline (vertical rail + kind dots),
  entity chips, SVG graph (flowing edges, breathing focus halo), AI Insights (violet accent),
  Memory, StatusBadge (status→tone map incl. created/active/validated/escalated…, pulse dot).
  Fixed pre-existing overflow: long mono ids now truncate (title attr keeps full value);
  timeline timestamps no longer wrap.
- **Verification**: frontend 4-gate green (lint, typecheck strict, 74/74 tests, build). Live
  visual proof over seeded stack (compose data + host uvicorn + Vite): headless-Chrome captures
  of Home/Dashboard/Workspace in dark **and** light themes — live findings/evidence/timeline/
  memory all rendered. Gotcha for future verification: `--virtual-time-budget` screenshots
  freeze `.stagger` entrance animations at opacity 0 for late-mounting query data (false
  "empty region"); use real-time CDP capture (`Page.navigate` explicitly — headless `/json/new
  ?url=` opens about:blank) — the in-pane preview screenshot also times out on infinite
  animations.
