---
title: ADR-016 Investigation Tenant Scope
status: Accepted
date: 2026-07-17
decision-makers: SentinelAI Team
---

# ADR-016: Investigation Tenant Scope

## Status

**Accepted** (proposed and reviewed through RFC-002, under ADR-014).

---

## Context

authentication-authorization §6a defines the Investigation Access Scoping
Model and states it "is extensible to team and organization scopes: a scope is
always expressed as an attribute of the investigation, evaluated by the
authorization policy." Milestone E (multi-tenancy) requires that extension so
one organization's investigations are isolated from another's. RFC-002 proposed
the tenant scope; this ADR records the accepted decision.

---

## Decision

### 1. The Investigation carries a tenant scope attribute

`Investigation` gains `tenant: TenantId` — a typed scope key. It is
**caller-supplied** from the authenticated identity (the caller-supplies-
identifiers rule is unaffected; the domain generates nothing). The tenant is an
opaque scope label, not a managed entity: tenant lifecycle and membership are
owned by the identity provider, outside the platform.

### 2. Identity carries a tenant

An authenticated identity carries a `tenant`. The production JWT authenticator
reads it from the `tenant` claim; the dev authenticator and claim-less tokens
use a single default tenant (`"default"`), so single-tenant deployments and the
existing dev flow are unchanged.

### 3. The authorization policy enforces tenant isolation

For an investigation-scoped operation, the policy permits access only when:

- the identity's tenant **equals** the investigation's tenant (cross-tenant →
  403 — the isolation boundary), **and**
- the existing owner rule holds (§6a, ES-046).

Tenant isolation is an **added conjunct** over owner scoping — a strengthening,
never a relaxation. Existence handling stays with the owning service (a missing
investigation is the service's 404, as before). The policy still consults only
the Investigation Service interface (AC-07).

### 4. Creation places the investigation in the creator's tenant

On create, the investigation's tenant is the authenticated identity's tenant
(as owner is the authenticated subject, ES-062) — a client cannot create an
investigation in a foreign tenant.

### 5. Migration backfills existing data to the default tenant

The `investigation.tenant` column is added NOT NULL with a server default of
`"default"`, backfilling existing rows. The default matches the dev/claim-less
identity tenant, so all existing investigations stay accessible after the
upgrade.

### 6. Scope boundaries (unchanged here)

- **Shared knowledge layers** (Memory, Knowledge Graph) remain open to
  authenticated identities; a per-tenant organizational-knowledge model is a
  documented follow-up (RFC-002 Scope Boundary), not decided here.
- **AC-14 preserved**: creation writes one store; the tenant rides the
  Investigation row.

---

## Rationale

- §6a already fixed the model ("a scope expressed as an attribute of the
  investigation, evaluated by the policy"); this realizes it without inventing
  new semantics.
- Layering tenant as an added conjunct keeps the change safe: no existing
  access is broadened, and the owner rule is untouched.
- An opaque scope label (vs a Tenant entity + membership) keeps the platform
  honest about complexity — the entity arrives only with a documented need.

---

## Alternatives Considered

See RFC-002 (infer tenant from data; replace owner scoping; a full Tenant
entity now) — all dismissed there with rationale.

---

## Consequences

### Positive

- Organization-level isolation: cross-tenant investigation access is denied.
- The change is additive and backward-compatible (default-tenant backfill).
- The tenant scope flows through the existing operation-context mechanism
  (§6b) — no new propagation path.

### Negative

- Shared knowledge layers are not yet tenant-scoped (a known follow-up).
- A single default tenant means the dev flow is single-tenant until tokens
  carry explicit tenants.

### Trade-Offs

The platform accepts an opaque scope label now and a managed Tenant entity
later — the same interim/production split it accepted for identity (dev token →
JWT) and storage (filesystem → object store).

---

## Related Documents

- RFC-002 Investigation Tenant Scoping
- authentication-authorization (§6a Investigation Access Scoping Model, §6b
  Operation Context)
- ADR-003 Polyglot Persistence (amended: Investigation carries a scope
  attribute)
- ADR-014 Lightweight Architectural Proposal Process
- ES-062 (production identity — the tenant claim rides the JWT)

---

## Notes

This ADR **amends ADR-003** by adding a scope attribute to the Investigation;
ADR-003's ownership model is otherwise unchanged. ADR-003's text is preserved
as a historical record (the ADR-011/ADR-015 precedent).

---

## Supersedes

None
