---
title: ADR-021 Release Identity and Compatibility
status: Accepted
date: 2026-07-26
decision-makers: SentinelAI Team
---

# ADR-021: Release Identity and Compatibility

## Status

**Accepted** — recorded directly as an ADR, without an RFC. ADR-014 §1 requires
an RFC only for proposals that supersede or amend an accepted ADR, change a
layer boundary or an enforced constraint, change domain-model semantics, or
introduce a new service or persistence category. This decision does none of
those: it governs how the platform is *versioned and released*, leaving every
architectural boundary untouched. The `Proposed → Accepted` transition is the
discussion stage, as ADR-014 intends.

---

## Context

The platform can build, scan, sign and publish versioned images (ES-068), and
it can say which stores it is ready to serve (ES-069/070). It cannot say **what
it is**. Three version numbers exist and none of them agrees with the others:
the backend distribution declares `0.1.0`, the frontend package declares
`0.0.0`, and the published image tags come from git tags that nothing checks
against either. Nothing states what a version change promises to a consumer,
which surface that promise covers, or how a built artifact becomes a running
release.

That gap has three concrete costs. An operator cannot tell which platform
version a deployment is running, because there is no such thing as *the*
platform version. A consumer of the API cannot tell whether an upgrade is safe,
because no compatibility surface is named. And a release is whatever someone
deploys: CI produces artifacts, but the decision to run one is unrecorded and
unverified.

Release Management (§4/§5/§8) defines release stages, ownership and readiness in
the abstract, and deliberately does not decide these questions. This ADR decides
them.

---

## Decision

### 1. The platform has one version, and every deployment unit declares it

SentinelAI releases as a **single platform**, not as independently versioned
units. The backend, the frontend and the published images carry the same
version number, and a release tag `vX.Y.Z` names that version.

The units are not independently versionable because they are not independently
usable: the frontend speaks exactly one API contract, and both are built and
published by the same pipeline from the same commit. Versioning them separately
would advertise an independence the architecture does not provide.

Agreement between the declared versions is **mechanically checked** (AC-16), so
a unit whose manifest falls behind is a failing test rather than a discovery
made during an incident.

### 2. The committed API contract is the compatibility surface

`docs/api/openapi.json` — kept current by constraint (AC-15) — **is** what a
version promises. Compatibility is defined against that artifact and nothing
else.

Explicitly outside the promise: the Planner Action Resource (already documented
as transitional, api-design), the operational endpoints (`/health`, `/health/ready`,
`/metrics`) which answer an orchestrator rather than a client, the database
schema, internal module structure, and the content of AI-generated output.

### 3. What a version change promises

Semantic Versioning, with the surface above as its subject:

- **MAJOR** — a change that can break a conforming consumer: removing or
  renaming an endpoint, field or error code; narrowing an accepted input;
  changing the meaning of an existing field.
- **MINOR** — new capability that a conforming consumer can ignore: new
  endpoints, new optional fields, new enum members in *output* positions.
- **PATCH** — behaviour-preserving fixes.

**Before 1.0.0 the platform promises nothing.** A `0.x` release may break any of
the above, which is precisely what the leading zero means; the compatibility
commitment begins with the first major release.

Removal is a two-step path: a surface is marked deprecated in the contract in a
MINOR release and removed no earlier than the next MAJOR.

### 4. A release is a verified, digest-pinned promotion, not a build

CI produces a **candidate**: an image that is scanned, described by an SBOM,
attested and signed. Promoting a candidate to an environment is a separate,
governed act (release-management §5) that:

- resolves the candidate to an immutable **digest** and deploys that digest,
  never a moving tag,
- **verifies the signature and the attestations before deployment**, so what is
  deployed is provably what the pipeline produced,
- is **explicitly authorized** (an environment approval), because deciding to
  run an artifact is a different responsibility from producing one, and
- leaves a **record** of who promoted which digest to which environment.

A tag is a convenience for humans; a digest is the release identity for
machines. Deployments follow digests.

### 5. The release record is human-readable and lives in the repository

A changelog records what each release contains, in the repository, next to the
code it describes. The engineering history stays in the maintainer's tracker;
the changelog is the consumer-facing account of a version.

---

## Rationale

- One platform version is the honest model: the units ship together, from one
  commit, through one pipeline, speaking one contract. Independent version
  numbers would be a claim about independent evolution that the deployment
  architecture does not support.
- Naming the compatibility surface makes the promise checkable. "The API is
  stable" is unverifiable; "the committed contract artifact is stable, and it is
  regenerated by constraint" can be inspected in a diff.
- Excluding the operational endpoints and the planner resource keeps the promise
  narrow enough to be *kept*. A commitment that covers everything is abandoned
  at the first inconvenience.
- Deploying digests rather than tags is what makes the signature meaningful: a
  verified tag can be re-pointed at unverified content a minute later.
- Separating "produce" from "promote" mirrors the responsibility split the
  release model already describes (§6): the pipeline owns artifact integrity,
  the release owner owns the decision to run it.
- The `0.x` disclaimer is a deliberate refusal to over-promise before the first
  release: pre-1.0 the platform is still deciding its surface, and pretending
  otherwise would make the first real commitment worthless.

---

## Alternatives Considered

### Version each deployment unit independently

Backend, frontend and images evolving on their own version lines.

Appropriate when units are separately consumable and separately deployable.
Neither holds here: the frontend targets one contract version and both images
are published together from one commit. It would also multiply the
compatibility question by the number of units without answering it once.

**Decision:** Rejected.

### Treat the entire HTTP surface as the compatibility promise

Including the operational endpoints and the planner action resource.

Health, readiness and metrics exist for an orchestrator and a scraper and must
stay free to change with operational needs; the planner resource is already
documented as transitional. Committing to them would either freeze operational
evolution or make the commitment routinely violated — the two ways a
compatibility promise dies.

**Decision:** Rejected.

### Deploy moving tags (`latest`, `X.Y`) and verify at build time only

Simplest to operate, and it severs the link between what was verified and what
runs: a tag is mutable, so signature verification at build time says nothing
about the bytes an environment will pull later.

**Decision:** Rejected.

### Continuous deployment on every green build

Attractive for cadence, and it removes the authorization step this decision
exists to create. With no hosted environment and one maintainer, it would also
automate a decision nobody has asked to have automated.

**Decision:** Rejected for now; the promotion mechanism does not preclude it.

---

## Consequences

### Positive

- A deployment can be asked what it is, and every artifact, tag and manifest
  answers the same way.
- The compatibility promise is inspectable in the same diff that changes it
  (AC-15), rather than being a claim in prose.
- What runs in an environment is provably what the pipeline built and signed.
- Every promotion has an owner and a record — release traceability
  (release-management §8) stops depending on memory.

### Negative

- Every release touches multiple manifests. The agreement check makes a
  forgotten one a failing test rather than a silent inconsistency, but the
  chore is real.
- A single platform version means a frontend-only fix still ships a backend
  version bump. That is the cost of an honest coupling model, not a defect.
- Promotion requires a configured environment with an approver; until one
  exists, the mechanism is exercised rather than operated.

### Trade-Offs

A narrow compatibility surface is accepted in place of a broad one: consumers
get a promise the project can actually keep, at the cost of leaving the
operational and transitional surfaces free to change without a major release.

---

## Related Documents

- Release Management (§4a Release Identity, §5a Promotion, §8a Release Record)
- API Design §14a Contract Synchronization (the compatibility surface and how it
  is kept current)
- Architecture Testing (AC-15 contract freshness; AC-16 governance consistency,
  which covers the version agreement)
- Deployment Architecture / Environment Architecture (what a promotion targets)
- ADR-014 Lightweight Architectural Proposal Process (why this ADR carries no
  RFC)
- `infrastructure/README.md` (registry, tags, signature verification — the
  technology specifics this decision deliberately does not carry)

---

## Notes

This ADR decides release governance only. It changes no layer boundary, no
domain semantics and no service ownership, and it introduces no new
architectural constraint — the version-agreement check is an application of
AC-16 (governance artifacts stay consistent), not a new rule.

---

## Supersedes

None
