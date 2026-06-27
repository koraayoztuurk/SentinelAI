---
title: ADR-006 Retrieval-Augmented Generation (RAG) Architecture
status: Accepted
date: 2026-06-27
decision-makers: SentinelAI Team
---

# ADR-006: Retrieval-Augmented Generation (RAG) Architecture

## Status

**Accepted**

---

## Context

Cybersecurity investigations require AI models to reason over organization-specific knowledge rather than relying solely on pretrained model knowledge.

Relevant information may include:

- previous investigations
- internal documentation
- threat intelligence
- analyst knowledge
- historical findings

Language models alone cannot reliably access this information.

An architecture was required to provide contextual knowledge while preserving explainability and traceability.

---

## Decision

SentinelAI adopts a Retrieval-Augmented Generation (RAG) architecture.

Relevant investigation context is retrieved before language model execution.

The retrieved context is transformed into structured prompts consumed by AI components.

The RAG pipeline consists of:

- Query Generation
- Retrieval
- Context Building
- Prompt Construction
- Language Model Execution

Each stage owns a distinct responsibility.

---

## Rationale

Separating retrieval from generation provides:

- evidence-backed reasoning
- improved explainability
- reusable retrieval components
- better prompt quality
- reduced hallucinations

The architecture ensures AI responses remain grounded in organizational knowledge rather than relying exclusively on model parameters.

---

## Alternatives Considered

### Prompt-Only Generation

Allowing language models to answer without external knowledge was considered.

This approach increases hallucination risk and prevents organization-specific reasoning.

**Decision:** Rejected.

---

### Direct Vector Retrieval

Passing retrieved documents directly to the language model without intermediate processing was considered.

This reduces architectural complexity but provides limited control over context quality and prompt structure.

**Decision:** Rejected.

---

### Fine-Tuned Language Models

Encoding organizational knowledge directly into model weights was considered.

This approach complicates knowledge updates and reduces flexibility as organizational knowledge evolves.

**Decision:** Rejected.

---

## Consequences

### Positive

- Improved factual grounding.
- Reduced hallucination risk.
- Better explainability.
- Reusable retrieval pipeline.
- Easier knowledge updates.

---

### Negative

- Additional retrieval latency.
- More architectural components.
- Greater implementation complexity.

---

### Trade-Offs

The architecture accepts increased execution complexity in exchange for higher investigation quality, transparency and maintainability.

---

## Related Documents

- RAG Architecture
- Memory Service
- Planner Agent
- AI Runtime
- Knowledge Graph

---

## Notes

The RAG pipeline provides contextual knowledge to AI components.

It does not replace organizational memory or business ownership.

Retrieval should always prioritize validated knowledge over generated assumptions.

---

## Supersedes

None