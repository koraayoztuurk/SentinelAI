---
title: RFC-002 Investigation Tenant Scoping
status: Accepted
date: 2026-07-17
decision-makers: SentinelAI Team
---

# RFC-002: Investigation Tenant Scoping

> Single-page RFC per ADR-014 §2. Required because the proposal **changes
> domain-model semantics (ownership / scoping)** — ADR-014 threshold (c).

## Status

**Accepted** (self-review per ADR-014 §3: evaluated against the design
principles and the Architecture Testing constraint catalogue; rationale below).

---

## Problem

authentication-authorization §6a fixes the Investigation Access Scoping Model:
"ownership is the initial access-scoping key … the model is **extensible to
team and organization scopes**: a scope is always expressed as an attribute of
the investigation, evaluated by the authorization policy — never inferred from
data content." Milestone E (multi-tenancy) needs that extension: today an
investigation is scoped only by its owner, so the platform cannot isolate one
organization's investigations from another's. No decision record admits a
tenant scope.

---

## Proposed Change

Add a **tenant** scope as an attribute of the Investigation, evaluated by the
authorization policy as an isolation boundary layered over the existing owner
rule.

- **Domain**: `Investigation` gains `tenant: TenantId` — a typed scope key,
  caller-supplied from the authenticated identity (never generated, consistent
  with the caller-supplies-identifiers rule).
- **Identity**: an authenticated identity carries a `tenant` (the JWT `tenant`
  claim; the dev authenticator and claim-less tokens use a single default
  tenant, so single-tenant deployments are unchanged).
- **Authorization** (§6a "a scope … evaluated by the authorization policy"):
  an investigation-scoped operation is permitted only when the identity's
  tenant **matches** the investigation's tenant (cross-tenant access → 403),
  **and** the existing owner rule holds. Tenant isolation is an added
  conjunct — a strengthening, never a relaxation of owner scoping.
- **Creation**: the created investigation's tenant is the creator's tenant
  (like owner==subject, ES-062) — a client cannot place an investigation in a
  foreign tenant.
- **Migration**: existing investigations are backfilled to the default tenant,
  so no current data becomes inaccessible.

## Affected ADRs / Constraints

- **ADR-003 (amended, via ADR-016)**: the Investigation carries a scope
  attribute; ownership assignment is unchanged, tenant is additive.
- **Domain-model semantics**: `Investigation` gains a field — the reason this
  needs an RFC (ADR-014 threshold c).
- **AC-14 preserved**: creation still writes one store; the tenant travels on
  the same Investigation row.
- **AC-07 preserved**: the policy still consults only the Investigation
  Service interface for the investigation's scope.

## Scope Boundary (explicitly out)

- **Shared knowledge layers** (organizational Memory, the Knowledge Graph)
  remain open to authenticated identities. §6a places their isolation boundary
  at *promotion*, not retrieval; a **per-tenant** promotion/retrieval model
  (organizational learning scoped to one organization) is a real follow-up
  question but is **not** decided here — it would need its own RFC. This RFC
  isolates investigation-scoped access only.
- **Tenant lifecycle** (creating/managing tenants, tenant membership, moving an
  investigation between tenants) is out: a tenant is an opaque scope label
  supplied by the identity provider, not a managed platform entity.

## Alternatives Dismissed

- **Infer tenant from data** (e.g. the owner's org): §6a forbids inferring a
  scope from data content — the scope must be an explicit attribute.
- **Replace owner scoping with tenant scoping**: this would *relax* isolation
  (any tenant member could read any investigation); the owner rule stays, tenant
  is layered on top.
- **A separate Tenant entity + membership tables now**: speculative — no current
  capability manages tenants; the opaque scope label is sufficient and the
  entity can arrive with a documented need.

## Acceptance Criteria

- ADR-016 records the decision; authentication-authorization §6a notes the
  realization.
- Cross-tenant access to an investigation-scoped surface is denied (403); the
  owner flow within a tenant is unchanged; existing (backfilled) investigations
  stay accessible to the default tenant.
- All verification gates green; the migration applies cleanly with a backfill.
