---
title: Release Management
version: 1.3.0
status: Accepted
owner: SentinelAI Team
last_updated: 2026-07-27
---

# Release Management

> This document defines the architectural model governing release progression throughout SentinelAI. It establishes release responsibilities, release lifecycle and release integrity while remaining independent of implementation technologies.

---

# 1. Purpose

Release Management defines how architectural changes progress throughout the SentinelAI operational lifecycle.

Rather than prescribing deployment pipelines, release automation or delivery technologies, this document establishes the architectural responsibilities governing release progression, release readiness and operational release integrity.

Release Management complements the Deployment Architecture, Environment Architecture and Configuration Management by defining how architectural changes advance through operational environments while preserving deployment ownership, environment responsibilities and configuration consistency.

Release progression should strengthen operational confidence without modifying the architectural responsibilities established throughout SentinelAI.

---

# 2. Design Goals

The Release Management architecture is designed to achieve the following goals.

## Controlled Release Progression

Architectural changes should progress through the operational lifecycle in a predictable and controlled manner.

Release progression should strengthen operational confidence while preserving platform stability.

---

## Explicit Release Ownership

Every release should have clearly defined architectural ownership.

Release ownership should remain aligned with the deployment units and architectural domains responsible for the released capabilities.

---

## Release Integrity

Every release should preserve the architectural integrity of the platform.

Operational delivery should never compromise architectural ownership, deployment boundaries or environment responsibilities.

---

## Operational Readiness

Architectural changes should demonstrate sufficient operational readiness before progressing through the platform lifecycle.

Operational readiness strengthens release confidence and reduces operational uncertainty.

---

## Independent Evolution

Release activities should support the independent evolution of deployment units whenever architectural responsibilities permit.

---

## Technology Independence

Release principles should remain independent of deployment automation, orchestration platforms and operational tooling.

---

# 3. Architectural Role

Release Management establishes the architectural model governing operational release progression throughout SentinelAI.

Rather than defining release automation mechanisms, the architecture identifies:

- release responsibilities
- release progression
- release lifecycle
- release readiness
- release integrity
- operational release consistency

Release Management does not define deployment automation, infrastructure provisioning, configuration technologies or operational tooling.

Those implementation concerns remain outside the scope of this architectural document.

The release model should remain consistent with the Deployment Architecture, Environment Architecture and Configuration Management while preserving architectural ownership, operational consistency and deployment independence.

---

# 4. Release Model

The Release Model defines how architectural changes progress through the operational lifecycle of SentinelAI while preserving architectural integrity, deployment ownership and operational consistency.

A release represents an operational progression of architectural capabilities rather than an implementation-specific deployment event.

A release governs progression without becoming the owner of the architectural capabilities it advances.

Release progression should strengthen operational confidence without modifying the architectural responsibilities established throughout the platform.

The release model is founded on the following principles:

- explicit release ownership
- controlled release progression
- operational readiness
- release integrity
- architectural consistency

---

## Release Boundaries

Release boundaries define the operational scope within which architectural changes progress together.

A release boundary represents an operational progression responsibility rather than a deployment, infrastructure or configuration boundary.

Each release boundary should:

- preserve deployment ownership
- maintain environment consistency
- support controlled operational progression
- reinforce architectural integrity
- preserve configuration consistency

Release boundaries should prevent unrelated operational changes from becoming unnecessarily coupled.

---

## Release Readiness

Every release should demonstrate sufficient operational readiness before progressing through the operational lifecycle.

Release readiness evaluates whether architectural changes remain compatible with:

- deployment responsibilities
- environment responsibilities
- configuration consistency
- operational expectations

Readiness should be determined by architectural confidence rather than operational convenience.

---

## Release Consistency

Equivalent architectural changes should follow equivalent release principles.

Operational progression should remain predictable regardless of deployment technologies or operational environments.

Maintaining release consistency simplifies governance, operational reasoning and long-term platform evolution.

---

## Controlled Release Progression

Architectural changes should progress deliberately throughout the operational lifecycle.

Release progression should preserve:

- deployment ownership
- architectural consistency
- operational stability
- environment integrity

Controlled release progression reduces operational uncertainty while preserving platform resilience.

---

# 4a. Release Identity and Compatibility (ADR-021, Normative)

A release must be identifiable, and what it promises must be stated. This section records the decision (ADR-021); the registry, tag scheme and verification commands remain technology specifics and live with the deployment infrastructure.

## One Platform Version

SentinelAI releases as a **single platform**, not as independently versioned deployment units. Every deployment unit declares the same version, and a release tag `vX.Y.Z` names it.

The units are not independently versioned because they are not independently usable: the presentation unit speaks exactly one version of the API contract, and both units are built and published from the same commit by the same pipeline. Independent version lines would advertise an independence the Deployment Architecture does not provide.

Agreement between the declared versions is mechanically verified (Architecture Testing, AC-16), so a manifest left behind is a failing check rather than an operational surprise.

**A version change is also a contract change.** The platform reports its version through the API, so the version appears inside the committed contract artifact (API Design §14a) — bumping the version therefore requires regenerating that artifact, and AC-15 fails the build until it is. This is a deliberate coupling rather than an inconvenience: it means a release version can never be claimed anywhere the published contract does not already state it.

## The Compatibility Surface

The committed API contract artifact (API Design §14a), kept current by constraint, **is** the surface a version promises. Compatibility is defined against that artifact and nothing else.

Deliberately outside the promise:

- the Planner Action Resource, already documented as transitional
- the operational endpoints (liveness, readiness, metrics), which answer an orchestrator and a scraper rather than a client
- the persistence schema and internal module structure
- the content of AI-generated output

A promise narrow enough to keep is worth more than a broad one that is quietly abandoned.

## What a Version Change Promises

- **MAJOR** — a change that can break a conforming consumer: a removed or renamed endpoint, field or error code; a narrowed input; a changed meaning for an existing field.
- **MINOR** — new capability a conforming consumer can ignore: new endpoints, new optional fields, new output enum members.
- **PATCH** — behaviour-preserving fixes.

**Before the first major release the platform promises nothing** — that is what the leading zero means. Removal follows a two-step path: deprecation announced in a MINOR release, removal no earlier than the next MAJOR.

---

# 5. Release Stages

Release Management recognizes multiple logical stages of operational progression.

Release stages describe the architectural maturity of a release rather than implementation-specific delivery pipelines.

---

## Candidate Stage

The Candidate Stage represents architectural changes that have completed implementation and are undergoing operational validation.

Its responsibilities include:

- demonstrating architectural readiness
- validating operational behavior
- confirming deployment compatibility
- supporting controlled progression

Candidate releases should remain isolated from operationally critical workloads until sufficient confidence has been established.

---

## Validation Stage

The Validation Stage evaluates the operational suitability of architectural changes.

Its responsibilities include:

- validating operational consistency
- confirming environment compatibility
- evaluating configuration behavior
- strengthening operational confidence

Validation should preserve architectural ownership while identifying issues before broader operational adoption.

---

## Operational Stage

The Operational Stage represents releases that are ready to provide production capabilities.

Its responsibilities include:

- delivering operational functionality
- preserving platform stability
- maintaining architectural consistency
- supporting operational continuity

Operational releases should prioritize platform reliability while preserving deployment independence.

---

## Evolution Stage

The Evolution Stage governs the ongoing operational maturity of released architectural capabilities.

Its responsibilities include:

- supporting future architectural improvements
- enabling controlled operational evolution
- preserving release integrity
- maintaining long-term platform consistency

Operational evolution should remain compatible with the architectural principles established throughout SentinelAI.

---

## Relationship Between Release Stages

Release stages represent increasing levels of operational confidence rather than different architectural models.

Every release stage preserves the same architectural ownership, deployment boundaries and operational responsibilities while supporting progressively greater operational maturity.

Release stages differ in operational maturity rather than architectural responsibility.

---

## 5a. Promotion Between Stages (ADR-021, Normative)

Stages describe maturity; **promotion** is the act of moving a release from one to the next. Producing an artifact and deciding to run it are different responsibilities (§6), so promotion is explicit rather than a side effect of a successful build.

Every promotion:

- **targets an immutable artifact identity.** A release is promoted by digest, never by a moving tag: a tag can be re-pointed after it was verified, so a tag-following deployment cannot know what it is running. Tags remain a convenience for humans.
- **verifies integrity before deployment, not only at production time.** The artifact's signature and its supply-chain attestations are checked at the moment of promotion. Verifying only where the artifact was built proves nothing about the bytes an environment later pulls.
- **is explicitly authorized.** Promotion requires the approval of the release owner for the target environment. Authorization is a release responsibility, not a pipeline capability.
- **leaves a record.** Who promoted which artifact identity to which environment, and when — the traceability §8 requires, independent of anyone's memory.

A promotion that cannot verify its artifact does not proceed. Refusing to deploy an unverifiable artifact is the mechanism working, not an outage.

Promotion carries no environment-specific behaviour: the same verified artifact identity progresses through environments, and only configuration differs (Configuration Management, Environment Architecture).

---

# 6. Release Responsibilities

Release responsibilities define the architectural ownership of release progression throughout SentinelAI.

Rather than assigning release ownership to deployment pipelines, automation platforms or operational tooling, the architecture assigns responsibility according to the architectural domains and deployment units responsible for the released capabilities.

Every release should have a clearly identified owner responsible for its operational progression, architectural consistency and lifecycle integrity.

Release ownership should remain independent of the technologies used to deliver the release.

Release responsibilities should remain explicit and should never become implicitly shared across unrelated architectural domains.

---

## Platform Release Responsibilities

Platform releases are responsible for:

- preserving platform-wide architectural consistency
- coordinating platform-level operational evolution
- maintaining platform integrity
- supporting long-term operational stability

Platform releases should evolve according to the operational objectives of the entire platform.

---

## Deployment Release Responsibilities

Deployment releases are responsible for:

- progressing deployment-specific capabilities
- preserving deployment compatibility
- maintaining deployment independence
- supporting controlled operational evolution

Deployment releases should remain owned by the deployment units responsible for the released capabilities.

---

## Environment Release Responsibilities

Environment releases are responsible for:

- supporting controlled operational progression
- preserving environment responsibilities
- maintaining operational consistency
- validating environment readiness

Environment releases should always respect the operational purpose of each environment.

---

## Domain Release Responsibilities

Each architectural domain is responsible for the release progression of its own capabilities.

Domain responsibilities include:

- maintaining architectural consistency
- preserving operational ownership
- minimizing unnecessary release dependencies
- remaining compatible with platform-wide release principles

Release ownership should always remain within the architectural domain responsible for the released capability.

---

## Cross-Domain Responsibilities

All architectural domains contribute to a consistent release model.

Shared responsibilities include:

- preserving release boundaries
- maintaining release integrity
- respecting release ownership
- minimizing unnecessary operational coupling
- supporting controlled release progression

Cross-domain collaboration should strengthen platform evolution without weakening architectural ownership.

---

# 7. Release Principles

The architecture establishes the following principles for governing release progression throughout SentinelAI.

These principles remain independent of deployment automation, delivery pipelines and operational tooling.

---

## Explicit Release Ownership

Every release should have a clearly identified architectural owner.

Release ownership should remain stable throughout the release lifecycle and should never become ambiguous as the platform evolves.

---

## Controlled Progression

Release progression should remain deliberate, predictable and understandable.

Progression should preserve:

- deployment ownership
- environment responsibilities
- configuration consistency
- architectural integrity

Controlled progression improves operational confidence while reducing release risk.

---

## Release Isolation

Release activities should remain appropriately isolated.

Releasing one architectural capability should not unnecessarily require unrelated deployment units or architectural domains to progress simultaneously.

Release isolation strengthens deployment independence and operational resilience.

---

## Operational Readiness

Every release should demonstrate sufficient operational readiness before progressing.

Operational readiness should confirm that the released capabilities remain compatible with:

- deployment responsibilities
- environment responsibilities
- operational expectations
- collaborating architectural domains
- configuration responsibilities

Readiness should strengthen confidence without weakening independent evolution.

---

## Release Consistency

Equivalent architectural capabilities should progress according to equivalent release principles.

Release consistency simplifies governance, operational reasoning and long-term platform evolution.

---

## Architectural Integrity

Release progression should preserve the architectural model established throughout SentinelAI.

Operational release activities should never redefine architectural ownership, deployment boundaries or responsibility allocation.

Maintaining architectural integrity ensures that operational progression remains a consequence of architecture rather than an architectural authority.

---

# 8. Release Lifecycle

Release Management supports the operational lifecycle of SentinelAI by governing how architectural capabilities mature from implementation to sustained operational use.

The Release Lifecycle defines how releases remain architecturally governed throughout their progression without prescribing implementation-specific delivery workflows or deployment automation.

Every release should remain understandable, traceable and operationally consistent throughout its lifecycle.

The architecture establishes the following lifecycle principles.

---

## Release Introduction

Every release should begin with a clearly defined architectural purpose.

Release introduction should establish:

- explicit release ownership
- operational objectives
- affected architectural responsibilities
- intended operational scope

No release should be introduced without an identified architectural responsibility.

---

## Release Evolution

A release may evolve as the operational needs of the platform change.

Release evolution should:

- preserve architectural integrity
- maintain operational consistency
- respect release boundaries
- minimize unnecessary operational impact

Release evolution should remain deliberate rather than incidental.

---

## Release Validation

Every release should be validated according to its architectural responsibilities before progressing further.

Validation should confirm that the release:

- preserves deployment ownership
- remains compatible with environment responsibilities
- maintains configuration consistency
- satisfies operational readiness
- preserves release ownership

Release validation strengthens confidence throughout the operational lifecycle.

---

## Release Retirement

Releases that no longer provide operational value should be retired in a controlled manner.

Retirement should:

- preserve architectural consistency
- eliminate obsolete operational behavior
- reduce unnecessary operational complexity
- maintain platform maintainability

Release retirement should never compromise architectural ownership or operational continuity.

---

## Lifecycle Traceability

The release lifecycle should remain understandable throughout platform evolution.

Release progression should remain attributable to its architectural responsibilities while preserving operational ownership and release integrity.

Lifecycle traceability supports architectural governance without prescribing implementation-specific release management technologies.

Release traceability should complement the architectural accountability established by Audit and Observability.

---

## 8a. Release Record (ADR-021, Normative)

Lifecycle traceability needs an artifact, not a practice. Every release carries a **human-readable record of what it contains**, kept in the repository beside the code it describes, so a consumer can learn what changed without reconstructing it from commit history.

The record states, per version: the capabilities added, the changes that affect a consumer of the compatibility surface (§4a) — including deprecations and removals — and anything an operator must do when upgrading (configuration or migration obligations).

The record is consumer-facing and deliberately distinct from the maintainer's engineering history, which carries decisions, trade-offs and technical debt. Two audiences, two artifacts: merging them makes the release record unreadable and the engineering record incomplete.

---

# 9. Extensibility

The Release Management architecture is designed to evolve together with SentinelAI while preserving its architectural release model.

Future architectural capabilities should integrate into the existing release model without altering release ownership, release progression or architectural integrity.

New release capabilities should:

- define explicit release ownership
- preserve release boundaries
- maintain operational consistency
- support controlled release progression
- remain compatible with deployment, environment and configuration responsibilities
- strengthen architectural governance

Architectural evolution should simplify release management rather than increase operational complexity.

---

# 10. Future Evolution

Future versions of the Release Management architecture may introduce:

- organization-specific release governance
- adaptive release progression strategies
- advanced release validation models
- release dependency analysis
- automated release governance
- release optimization strategies
- platform-wide release standardization

Future enhancements should preserve the architectural principles established by this document.

Regardless of future platform evolution, explicit release ownership, controlled progression and architectural integrity should remain fundamental characteristics of Release Management.

---

# 11. Design Principles Applied

The Release Management architecture follows the engineering principles established throughout SentinelAI.

| Principle | Release Management Application |
|-----------|--------------------------------|
| Human-Centered AI | Release progression supports reliable platform evolution while minimizing disruption for analysts and operators. |
| Explainability | Release ownership, progression and lifecycle remain explicit and understandable. |
| Separation of Responsibilities | Release Management governs operational progression without assuming deployment or architectural ownership. |
| Modularity | Releases evolve independently whenever architectural responsibilities permit. |
| Least Privilege | Release activities remain limited to the architectural responsibilities legitimately participating in the release. |
| Defense in Depth | Controlled release progression complements deployment, environment and security boundaries by reducing operational risk. |
| Architecture Before Framework | Release principles remain independent of deployment pipelines, automation platforms and delivery technologies. |

---

# Closing Statement

Release Management establishes the architectural foundation for governing operational progression throughout the SentinelAI platform lifecycle.

By defining release ownership, progression, operational readiness and lifecycle principles, the architecture enables predictable platform evolution while preserving deployment independence, environment consistency and architectural integrity.

This document complements the Deployment Architecture, Environment Architecture and Configuration Management by defining how architectural capabilities progress operationally without redefining architectural responsibilities.

Future release capabilities should extend these architectural principles while preserving explicit ownership, controlled progression and the Architecture First philosophy established throughout SentinelAI.

Release Management should continue to evolve together with the platform while preserving architectural integrity, operational consistency and explicit release ownership.

---

# Known Gaps (Release 1.0)

Recorded per ADR-020 §3: each item below is deliberately open. It states what the platform does today in its place and the governance path that would close it (documentation, ADR, or RFC per the ADR-014 threshold).

- **No environment is hosted, so promotion is exercised rather than operated.** The mechanism verifies an artifact and resolves it to an immutable identity, and the deployment it hands that identity to is a compose invocation on a machine somebody runs (Deployment Architecture). Approval is enforced by the hosting platform's environment protection, which is deployment configuration rather than repository content — a deployment that leaves it unconfigured has a mechanism without a gate.
- **Rollback is deployment-level, not release-level.** Promoting an earlier digest restores earlier code; whether it restores earlier *behaviour* depends on schema migrations, which are forward-only (Database Architecture). A release-level rollback contract needs the backup architecture that data-lifecycle §6 also waits for.
- **No release is signed as a release.** Images are signed and attested individually; the version itself — the claim "these two digests together are 1.0.0" — carries no signature of its own.
- **The release record is written by hand.** Nothing derives it from the contract diff, so a compatibility-affecting change reaches the changelog through review rather than by construction; AC-15 makes the diff visible, not the prose about it.

---

# Version History

| Version | Date | Description |
|----------|------------|--------------------------------|
| 1.0.0 | 2026-06-28 | Initial Release Management specification created |
| 1.1.0 | 2026-07-26 | Known Gaps section added (ADR-020 §3). The document **stays Draft** by the promotion rule (§2): release identity, the compatibility policy and the promotion path are normative content this document is missing rather than deferring, and they are the subject of the next engineering specification |
| 1.2.0 | 2026-07-26 | Release identity, compatibility and promotion decided (**ADR-021**, ES-072): §4a one platform version across every deployment unit (agreement verified by AC-16) with the committed API contract named as the compatibility surface and SemVer given a subject; §5a promotion as an explicit, authorized act on an immutable artifact identity, verified before deployment and recorded; §8a the human-readable release record. Status Draft → **Accepted** (ADR-020 §2): the content ES-071 recorded as missing is now present, and the Known Gaps section states what remains open |
| 1.3.0 | 2026-07-27 | §4a records that **a version change is also a contract change**: the platform reports its version through the API, so the committed contract artifact carries it and AC-15 fails until the artifact is regenerated. Written down because the release-preparation build discovered it the hard way — a bumped manifest with a stale artifact |
