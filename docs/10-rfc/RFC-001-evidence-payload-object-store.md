---
title: RFC-001 Evidence Payload Object Store
status: Accepted
date: 2026-07-17
decision-makers: SentinelAI Team
---

# RFC-001: Evidence Payload Object Store

> Single-page RFC per ADR-014 §2. Required because the proposal **amends an
> accepted ADR** (ADR-003's ownership map gains a storage technology) —
> ADR-014 threshold (a).

## Status

**Accepted** (self-review per ADR-014 §3: evaluated against the design
principles and the Architecture Testing constraint catalogue; rationale
recorded below).

---

## Problem

Database Architecture §8b designates a **content-addressed object store** as
the home of raw evidence payloads (uploaded files, raw log archives) and
explicitly requires "its own decision before introduction". Until now evidence
content is carried inline in the Evidence record — an accepted interim state,
not the target architecture. Milestone D (Evidence Ingestion) needs the
payload home to exist; no decision record admits it.

---

## Proposed Change

Admit a content-addressed object store as a **primary storage technology**
(ADR-011 category model) owning exactly one artifact kind: **raw evidence
payload bytes**, addressed by their content hash.

- The Evidence **record** (metadata + normalized content) and the integrity
  anchor remain owned by PostgreSQL through the Investigation Service
  (ADR-003 unchanged for all existing objects).
- Payload **access is mediated by the Investigation Service** (§8b rule 3):
  an application-layer port, a concrete infrastructure adapter, no other
  consumer.
- The Evidence record references its payload by content address — the
  existing `EvidenceIntegrity` value **is** the address (§8b rule 1); the
  domain model is unchanged.
- Scope boundary: this admits payload **storage and access** (upload
  transport for bytes, verified download). Format parsing and log
  normalization remain the deferred "evidence ingestion" capability of the
  Investigation Service boundary document and would need their own decision
  (and possibly a distinct service, ADR-004).

## Affected ADRs / Constraints

- **ADR-003 (amended):** the ownership map gains a fourth primary technology
  owning raw payload bytes only. Recorded in ADR-015; ADR-003's text is not
  rewritten (ADR-011 precedent).
- **AC-14 (no dual write) preserved:** payload upload (object store write)
  and evidence attach (PostgreSQL write) are separate operations, each
  writing one store; content-addressed put is idempotent, so upload retries
  and re-uploads are harmless. No request path writes two stores.
- **Caller-supplies-identifiers discipline unaffected:** the content address
  is a deterministic derivation from the payload bytes (a hash), not a
  generated identifier; the application computes it, the adapter never mints
  anything.
- **Clean Architecture:** port in the application layer (Investigation
  package), adapter in infrastructure — the ES-040/043 pattern; no layer
  boundary changes.

## Alternatives Dismissed

- **Keep payloads inline in PostgreSQL** — §8b names this an interim state;
  large immutable binaries in the record row defeat integrity anchoring and
  bloat the authoritative store.
- **Supporting-persistence category (ADR-011, like Redis)** — payloads are
  not reproducible from other stores; a "never authoritative" store cannot
  own them.
- **Introduce an S3/MinIO service now** — a real object-store deployment
  adds an infrastructure component no current capability needs; the port
  makes the swap a Milestone G (production hardening) concern. The first
  adapter is filesystem-backed and dev-grade, mirroring the accepted
  dev-auth precedent.

## Acceptance Criteria

- ADR-015 records the decision; database-architecture §8b notes the
  realization.
- Payload upload/download runs end to end through the Investigation Service
  with hash verification on read; all verification gates green.
- No existing evidence flow (inline content, non-address integrity values)
  changes behavior.
