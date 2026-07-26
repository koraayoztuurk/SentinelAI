---
title: ADR-019 Shared-Knowledge Erasure Authorization
status: Accepted
date: 2026-07-26
decision-makers: SentinelAI Team
---

# ADR-019: Shared-Knowledge Erasure Authorization

## Status

**Accepted** (proposed and reviewed through RFC-005, under ADR-014).

---

## Context

The person-linked erasure path for Memory Items and graph entities exists at the
service layer (ES-065, ADR-017 §4) but has no API surface. Exposing it needs an
authorization answer the platform did not have: authentication-authorization
§6a places the shared-knowledge isolation boundary at **promotion**, so any
authenticated identity may retrieve organizational knowledge — a rule that is
right for retrieval and unacceptable for destruction. The identity model carries
subject, kind and tenant and nothing about what an identity is permitted to do
beyond investigation ownership. Leaving the path unexposed keeps a legal
obligation reachable only through direct database access. RFC-005 proposed
granted capabilities and a gated surface; this ADR records the decision.

---

## Decision

### 1. An identity carries granted capabilities

The verified identity gains an immutable set of **capabilities**: opaque strings
asserted by the credential and evaluated by the authorization policy. A
credential asserting none — every credential issued before this decision —
yields an empty set, so the change is **behaviour-preserving by construction**.

Capabilities are an *authorization input*, not an identity attribute the
platform manages: the identity provider grants them, the platform reads them.

### 2. Destroying shared knowledge requires `knowledge:erase`

Erasing a Memory Item or a graph entity requires the `knowledge:erase`
capability. Retrieval, creation and promotion on the shared layers remain open
to any authenticated identity — §6a is unchanged. An identity without the
capability is refused by the existing authorization seam, indistinguishable in
shape from any other denial.

### 3. This is not a role model

The platform defines no roles, no role-to-permission mapping, no capability
administration surface and no capability storage. A full RBAC model — with its
own storage, administration and lifecycle — remains a separate decision, to be
taken on its own merits rather than as a side effect of gating one operation.

### 4. The gate is the capability, not the tenant

Memory and the Knowledge Graph carry no tenant (ADR-016 recorded per-tenant
organizational knowledge as an open follow-up), so a tenant match cannot scope
this operation. The capability alone gates it, and that limitation is recorded
rather than obscured: a reader must not infer an isolation the platform does not
provide.

### 5. Erasure through the surface is audited as an erasure

The operation is recorded under the erasure action category (ADR-018 §7), so the
record of who erased which knowledge item survives the erased data
(data-lifecycle §5).

### 6. The development authenticator grants capabilities by configuration

The development-grade shared-token authenticator grants a configured capability
set (empty by default). Possession of the shared secret already gates entry
there; a local deployment needs some way to exercise the gate without an
identity provider. The production JWT verifier reads the credential's claim.

---

## Rationale

- The question "who may erase organizational knowledge" needed an answer that is
  neither "everyone" (the §6a retrieval rule extended past its purpose) nor
  "nobody through the API" (the obligation exercised only via database access).
  A capability is the smallest construct that answers it.
- Consuming an authorization fact the IdP already owns keeps the platform out of
  identity management, consistent with authentication remaining a replaceable
  boundary concern.
- An empty capability set as the default means the decision cannot silently
  widen anything: every existing credential keeps exactly the access it had.
- Recording the untenanted limitation is part of the decision. A gate that looks
  like isolation but is not would be worse than no gate at all.

---

## Alternatives Considered

See RFC-005 (any authenticated identity; owner-of-the-knowledge; configured
subject lists; full RBAC now; leaving it service-layer-only; gating on identity
kind) — all dismissed there with rationale.

---

## Consequences

### Positive

- The right-to-be-forgotten path for shared knowledge becomes reachable through
  a governed, audited surface instead of a database console.
- The authorization model gains a general mechanism: future privileged surfaces
  gate on a capability rather than inventing a bespoke rule each time.
- No existing access changes; the default is empty and therefore closed.

### Negative

- Capabilities are only as trustworthy as the identity provider that asserts
  them: a mis-issued claim grants real destructive power. The platform's
  mitigation is that the claim rides a verified credential and the action is
  audited — not that it is second-guessed.
- The development authenticator's configured capabilities are a deployment
  convenience that must not reach production; the production selector (JWT) is
  the guard.
- Erasure remains untenanted: in a multi-tenant deployment, a holder of the
  capability can erase shared knowledge regardless of which tenant contributed
  it. This is the ADR-016 follow-up, now visible rather than latent.

### Trade-Offs

A minimal capability check is accepted in place of a complete authorization
model: it answers the question at hand without committing the platform to an
RBAC design it has not yet needed, at the cost of leaving richer authorization
semantics undecided.

---

## Related Documents

- RFC-005 Shared-Knowledge Erasure Authorization
- Authentication and Authorization (§6a Shared Knowledge Boundary, §7
  authorization responsibilities)
- Data Lifecycle and Erasure (§2 ownership, §5 audit exception)
- ADR-016 Investigation Tenant Scope (shared knowledge remains untenanted)
- ADR-017 Data Erasure and Tombstoning (the erasure path being exposed)
- ADR-018 Audit Lifecycle and Durable Sink (the erasure action category)

---

## Notes

This ADR **extends** the identity/authorization model additively: no existing
rule is relaxed, and the empty default preserves current behaviour exactly. It
does not supersede ADR-016; the untenanted nature of shared knowledge is
restated as a known limitation rather than resolved.

---

## Supersedes

None
