# Changelog

All notable changes to SentinelAI are recorded here. This is the
**consumer-facing** release record required by Release Management §8a; the
maintainer's engineering history (decisions, trade-offs, technical debt) lives
elsewhere and is deliberately not merged into it.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) as
scoped by **ADR-021**: the compatibility surface is the committed API contract
`docs/api/openapi.json`, and **a `0.x` version promises nothing** — the
commitment begins at 1.0.0.

Every deployment unit declares the same platform version, and a release tag
`vX.Y.Z` names it.

---

## [Unreleased]

Nothing yet.

---

## [1.0.0] - 2026-07-26

First release. Every deployment unit declares `1.0.0`, and the compatibility
promise described above begins here: from this version on, a breaking change to
`docs/api/openapi.json` requires a major release.

### Added

- **Investigation lifecycle** — investigations, evidence, findings, outcome and
  an append-only Investigation Trace, over PostgreSQL as the authoritative store.
- **AI-supported investigation** — an in-process AI Runtime with a planner-driven
  investigation loop, specialized agents (Validation, Graph Analysis, Threat
  Intelligence) and a Decision Engine that synthesizes an outcome. Every AI step
  lands in the Trace, so a conclusion can be explained rather than trusted.
- **Knowledge layer** — a Neo4j knowledge graph, versioned organizational memory,
  and retrieval (semantic, structured, graph and external) consumed by the agent
  path.
- **Threat intelligence** — a bundled MITRE ATT&CK catalog and live NVD CVE
  lookups behind a provider-neutral port.
- **Evidence payloads** — content-addressed upload and verified download,
  mediated by the Investigation Service and bounded by a configured maximum size.
- **Identity and multi-tenancy** — JWT authentication, owner-scoped
  authorization, tenant isolation, and granted capabilities gating destructive
  operations on shared knowledge.
- **Data end-of-life** — investigation erasure with tombstoning, secondary-store
  propagation (payload bytes, embeddings), person-linked knowledge erasure,
  automated retention enforcement (disabled unless a period is configured), and
  crypto-shredding for evidence payloads.
- **Production hardening** — circuit breakers with bounded retry on every
  provider edge, projection retry with an observable dead letter, per-identity
  rate limiting, a TLS edge, a hash-chained tamper-evident audit log, readiness
  gating on the authoritative stores, and `GET /api/v1/platform/status` reporting
  the platform's own operational posture.
- **Supply chain** — versioned images published to GHCR with a vulnerability
  gate, SPDX SBOM, SLSA provenance and a keyless signature.
- **Governance** — architecture documents carry a lifecycle and state their own
  known gaps; governance freshness, the API contract artifact and release
  identity are verified by the test suite.

### Notes for operators

- The backend image prepares its evidence-payload directory owned by the
  unprivileged runtime user. A named volume created by a **pre-release** image is
  root-owned and must be repaired once — see
  [`infrastructure/README.md`](infrastructure/README.md); a fresh deployment
  needs nothing.
- Retention enforcement is **off** unless `RETENTION_INVESTIGATION_DAYS` is set:
  no default retention period is correct, so none is assumed.
- Readiness gates on PostgreSQL **and** Neo4j; Qdrant is reported but never
  gates (its embeddings are reproducible).
- Deploy by digest, verifying the signature first — see
  [`infrastructure/README.md`](infrastructure/README.md).
