---
title: RFC-005 Shared-Knowledge Erasure Authorization
status: Accepted
date: 2026-07-26
decision-makers: SentinelAI Team
---

# RFC-005: Shared-Knowledge Erasure Authorization

> Single-page RFC per ADR-014 §2. Required because the proposal **adds an
> authorization dimension to the identity model** (an identity gains granted
> capabilities) and **opens a destructive surface on the shared-knowledge
> boundary** that authentication-authorization §6a deliberately left open for
> retrieval — ADR-014 thresholds (a) and (c).

## Status

**Accepted** (self-review per ADR-014 §3: evaluated against the design
principles and the Architecture Testing constraint catalogue; rationale below).

---

## Problem

ES-065 gave Memory Items and graph entities a person-linked erasure path
(right-to-be-forgotten, data-lifecycle.md §2 / ADR-017 §4) — at the **service
layer only**. It was deliberately not exposed, because exposing it requires
answering a question the platform had not answered: *who may erase
organizational knowledge?*

The current policy permits **any authenticated identity** to use
`/api/v1/memory` and `/api/v1/graph`. That is correct for retrieval:
authentication-authorization §6a places the isolation boundary at **promotion**,
not retrieval, precisely so that validated organizational knowledge is
cross-investigation. It is plainly wrong for destruction. Under the same rule,
an erasure endpoint would let any analyst destroy shared knowledge, and a
right-to-be-forgotten request would be indistinguishable from vandalism.

Leaving it unexposed is not neutral either. The erasure obligation is legal, and
today it can only be exercised by someone with **direct database access** — an
ungoverned, unaudited path that is strictly worse than a narrow, audited API.
The platform's identity model carries subject, kind and tenant, and no notion of
what an identity is *allowed* to do beyond investigation ownership, so there is
nothing for a policy to consult.

---

## Proposed Change

Give identities **granted capabilities**, and gate destructive shared-knowledge
operations on one.

- **An identity may carry capabilities.** The credential names them; the
  identity model carries them as an immutable set. A credential naming none —
  which is every credential issued today — yields an empty set, so **existing
  behaviour is unchanged by construction**.
- **Destroying shared knowledge requires the `knowledge:erase` capability.**
  Retrieval, creation and promotion on the shared layers stay open to any
  authenticated identity (§6a is untouched). Only the destructive operations are
  gated, and an identity without the capability is refused by the same
  authorization seam as any other denial (403).
- **This is deliberately not a role model.** Capabilities are opaque strings
  granted by the identity provider. The platform defines no roles, no
  role-to-permission mapping, no administration surface for them, and no
  storage: it *consumes* an authorization fact the IdP already owns. A full RBAC
  model remains a later decision.
- **The gate is the capability, not the tenant.** Memory and the Knowledge Graph
  carry no tenant (ADR-016 recorded per-tenant organizational knowledge as a
  follow-up), so a tenant match cannot scope this operation and pretending
  otherwise would manufacture a false sense of isolation. Stated explicitly so
  the limitation is visible rather than assumed away.
- **Erasure through the surface is audited as an erasure** (ADR-018 §7): who
  erased which knowledge item, when, with what outcome — the record outliving
  the erased data (data-lifecycle §5).
- **The development authenticator grants capabilities by configuration**
  (empty by default), consistent with its documented development-grade nature:
  possession of the shared secret already gates entry, and a local demo needs a
  way to exercise the gate without an identity provider.

## Affected ADRs / Constraints

- **ADR-019 (new):** records the capability dimension and the gated surface.
- **authentication-authorization.md (amended, §6a/§7):** the Shared Knowledge
  Boundary gains a destructive-operation rule; identity gains capabilities.
- **ADR-016 (referenced, unchanged):** shared knowledge remains untenanted; this
  RFC does not resolve that follow-up and says so.
- **ADR-017 / ADR-018 (realized):** the person-linked erasure path becomes
  reachable and audited under its own action category.
- **AC-07 preserved:** the policy consults no other service's persistence
  contracts — the capability travels on the identity, so no lookup is needed.
- **AC-14 preserved:** each erasure operation writes exactly one store; the
  derived embedding is erased through the existing outbox projection.

## Scope Boundary (explicitly out)

- **A role model / RBAC** — roles, hierarchies, role administration and their
  lifecycle. Out by decision, not by omission.
- **Per-tenant organizational knowledge** (the ADR-016 follow-up): still open;
  this RFC gates *who*, not *whose*.
- **Bulk or subject-wide erasure orchestration** ("erase everything about this
  person across every store") — each owning service exposes its own category's
  path, invoked per category (the ADR-017 boundary).
- **Capability administration inside the platform** (granting, revoking,
  listing): the IdP owns it; the platform reads what the credential asserts.

## Alternatives Dismissed

- **Keep the §6a rule and let any authenticated identity erase.** Consistent,
  and wrong: it makes destroying organizational knowledge exactly as easy as
  reading it, with no way to distinguish a compliance action from an accident.
- **Scope erasure to the "owner" of the knowledge.** Shared knowledge has no
  owner by construction — promotion is precisely the step that severs the link
  to the originating investigation (§6a). There is no owner to consult.
- **List permitted subjects in configuration.** Puts identity management in
  `.env`, does not survive staff changes, and re-answers the question every
  deployment instead of once.
- **Adopt a full RBAC model now.** A role model needs storage, administration,
  and a lifecycle of its own — the largest possible answer to the smallest
  question, and a platform capability that should be decided on its own merits.
- **Leave it service-layer-only.** The status quo: the obligation stays
  exercisable only through direct database access — ungoverned, unaudited, and
  unavailable to the people actually responsible for it.
- **Gate on `IdentityKind`.** Every analyst is a human identity; the distinction
  carries no authority signal.

## Acceptance Criteria

- ADR-019 records the decision; authentication-authorization.md notes the
  capability dimension and the destructive-operation rule on the shared
  boundary.
- An identity carries granted capabilities; a credential asserting none behaves
  exactly as before.
- Erasing a Memory Item or a graph entity through the API succeeds for an
  identity holding `knowledge:erase` and is denied (403) otherwise.
- The erasure is audited under the erasure action category.
- All verification gates green; AC-07 and AC-14 hold.
