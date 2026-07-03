---
title: SentinelAI Data Lifecycle and Erasure
version: 1.0.0
status: Draft
owner: SentinelAI Team
last_updated: 2026-07-03
---

# Data Lifecycle and Erasure

> This document defines how data ends its life within SentinelAI: retention, deletion and erasure obligations. It closes the gap between the platform's preservation-oriented architecture (immutable evidence, versioned memory, append-only trace and audit) and the legal reality that a security platform processes personal data that may have to be erased (audit finding M-05).

---

# 1. Purpose

The Memory, Domain and Audit architectures are deliberately preservation-first: evidence is immutable, knowledge is superseded rather than destroyed, and audit/trace records are append-only.

None of these principles removes the platform's erasure obligations. Investigation data (user activity, identities, network traffic) contains personal data; retention limits and erasure requests ("right to be forgotten") are external constraints the architecture must be able to satisfy **by design** — retrofitting erasure into an immutability-first model is not feasible later.

This document defines the lifecycle model; concrete retention values are deployment policy, not architecture.

---

# 2. Data Categories and Lifecycle Ownership

Every data category has a lifecycle owner — the backend service that owns the data (ADR-004). The owner is responsible for applying retention and executing erasure for its category.

| Data Category | Owner | End-of-Life Model |
|---|---|---|
| Investigation, Evidence, Finding, Report, Outcome | Investigation Service | Retention-bound archival, then erasure |
| Investigation Trace | Investigation Service | Follows its investigation's lifecycle |
| Memory Items (+ embeddings) | Memory Service | Deprecation (retrieval-invisible), then erasure; embeddings erased with their source item |
| Entities, Relationships | Graph Service | Deprecation, then erasure of person-linked data |
| Audit records | Platform (audit sink) | Retention-bound; legally privileged (see §5) |
| Cache (Redis) | Owning services | Expiry only — never a lifecycle concern (non-authoritative, ADR-011) |

---

# 3. Lifecycle Principles

## Retention Is Policy, Expiry Is Architectural

Every persistent data category must have a definable retention policy, and every owning service must expose an erasure path for its category. Which durations apply is configuration; **that** they can be applied is architecture.

## Deprecation Is Not Deletion

The existing deprecation/supersession mechanisms (Memory maturity model, entity deprecation) control *relevance*, not *existence*. A deletion path must exist independently of deprecation.

## Erasure Follows Ownership and References

Erasing an investigation erases its scoped objects (evidence, findings, reports, outcome, trace). Cross-store references (identifiers) may survive as **tombstones**: a reference that resolves to "erased" is explicit and observable — never silently repaired or hidden (consistent with Database Architecture §8a).

## Derived Data Is Erased With Its Source

Embeddings and other derived representations are erased when their authoritative source is erased — through the same propagation mechanism that created them (ADR-012 outbox; erasure is a projection like any other).

---

# 4. Erasure Strategies for Immutable Data

Immutability governs *modification*, not *end of life*. Two strategy categories are recognized:

- **Tombstoning** — the record is replaced by an explicit erasure marker preserving only non-personal correlation structure (identifiers, timestamps of the erasure itself). Suitable for evidence, findings and trace entries.
- **Cryptographic erasure (crypto-shredding)** — content is stored encrypted per erasure unit; destroying the key renders it unrecoverable. The designated strategy for large immutable payloads (Evidence Payload Storage, Database Architecture §8b) where physical deletion from content-addressed or append-only storage is impractical.

The choice per store is an adapter-level decision made when the store's adapter is implemented; the *existence* of an erasure strategy per category is mandatory.

---

# 5. Audit and Trace Exception

Audit records document security-relevant actions, including erasure itself, and may be legally required to survive erasure requests. The model:

- Erasure operations are themselves audited (who requested, what category, when).
- Audit records minimize personal data by design (subject identifiers, not content), narrowing the tension between audit retention and erasure obligations.
- Trace entries are investigation-scoped and follow the investigation's erasure; they are **not** part of the audit exception.

---

# 6. Boundaries

- This document defines no legal interpretation; mapping obligations (GDPR or otherwise) to categories is a deployment/compliance concern.
- Backup/restore interaction with erasure is deferred until a backup architecture exists — flagged here so it is decided with it, not after it.
- Concrete erasure implementation follows the persistence adapters (implementation tracker).

---

# Version History

| Version | Date | Description |
|----------|------------|--------------------------------|
| 1.0.0 | 2026-07-03 | Initial Data Lifecycle and Erasure specification (audit finding M-05): lifecycle ownership per category, deprecation≠deletion, tombstoning/crypto-shredding strategy categories, audit exception |
