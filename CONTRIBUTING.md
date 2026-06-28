# Contributing to SentinelAI

Thank you for your interest in contributing to SentinelAI.

SentinelAI is an architecture-first cyber investigation platform that emphasizes long-term maintainability, explicit architectural ownership and structured engineering practices.

Whether you are fixing a bug, improving documentation or proposing a new architectural capability, every contribution is appreciated.

Before contributing, please take a few minutes to familiarize yourself with the project's documentation and development philosophy.

---

## Guiding Principles

SentinelAI follows several core principles that guide every contribution:

* **Architecture First** — Architecture is designed before implementation.
* **Explicit Ownership** — Every architectural concept has a single, clearly defined owner.
* **Incremental Evolution** — The platform evolves through deliberate, incremental improvements.
* **Governance-Driven Development** — Architectural evolution is managed through RFCs and ADRs.
* **Long-Term Maintainability** — Short-term implementation convenience should never compromise long-term architecture.

These principles apply to documentation, implementation and architectural evolution alike.

---

## Before You Contribute

Before opening a Pull Request, please review the relevant documentation located in the `docs/` directory.

Depending on the nature of your contribution, you may also need to review:

* Project Charter
* System Overview
* Architectural Decision Records (ADRs)
* RFC Process
* Development Roadmap

Contributions should remain consistent with the approved architecture and established governance model.

---

## Contribution Workflow

Different types of contributions follow different workflows. Before making changes, determine which category best describes your contribution.

### Documentation Improvements

Examples:

* Fixing typos
* Improving explanations
* Updating diagrams
* Clarifying documentation

Workflow:

```text
Documentation Update
        ↓
Open Pull Request
        ↓
Review
        ↓
Merge
```

---

### Implementation Improvements

Examples:

* Bug fixes
* Performance improvements
* Refactoring
* Test improvements
* Implementing approved features

Workflow:

```text
Implementation Change
        ↓
Implement
        ↓
Open Pull Request
        ↓
Code Review
        ↓
Merge
```

Implementation changes should remain consistent with the approved architecture.

---

### Architectural Changes

Examples:

* New architectural capabilities
* Service boundary changes
* New architectural domains
* Significant AI workflow changes
* Architectural responsibility changes

Workflow:

```text
Architectural Proposal
        ↓
Create RFC
        ↓
Architecture Review
        ↓
RFC Accepted
        ↓
Create / Update ADR (if required)
        ↓
Implementation
        ↓
Pull Request
```

Architecture should always evolve before implementation.

---

## Architecture Changes

Architectural changes should never be introduced directly through implementation.

If your contribution changes the architecture of SentinelAI, begin by creating an RFC that describes:

* the motivation
* the proposed architectural evolution
* expected architectural impact
* alternatives considered
* migration strategy

After architectural review, accepted proposals may result in one or more Architectural Decision Records (ADRs).

Only after the governance process has been completed should implementation begin.

This process preserves architectural consistency, explicit ownership and long-term maintainability.

---

## Pull Requests

When submitting a Pull Request:

* Keep changes focused and self-contained.
* Reference the relevant Issue, RFC or ADR whenever applicable.
* Ensure documentation remains consistent with implementation.
* Avoid unrelated changes in the same Pull Request.
* Update documentation when architectural behavior changes.

Large architectural changes should not be introduced without first completing the RFC process.

Pull Requests are reviewed for both implementation quality and architectural consistency.

---

## Reporting Issues

If you discover a bug, unexpected behavior or documentation inconsistency, please open an Issue describing the problem.

A useful Issue should include:

* A clear description of the problem.
* Steps to reproduce the behavior (if applicable).
* Expected behavior.
* Relevant logs, screenshots or error messages.
* Any additional context that may help reproduce or understand the issue.

For architectural concerns, please explain which architectural principle, responsibility or document is affected.

Well-described Issues help maintain the quality and consistency of the project.

---

## Development Philosophy

SentinelAI is built on the belief that sustainable software begins with sustainable architecture.

Implementation should realize approved architectural decisions rather than redefine them.

Every contribution should strive to preserve:

* Architectural consistency
* Explicit ownership
* Clear responsibility boundaries
* Long-term maintainability
* Technology independence
* Incremental architectural evolution

Architecture is treated as a long-term asset. Every contribution should strengthen that foundation rather than introduce unnecessary complexity.

---

---

## Thank You

Thank you for taking the time to contribute to SentinelAI.

Whether you improve the documentation, fix a bug, refine the implementation or help evolve the architecture, your contribution helps make the project better.

Every meaningful contribution—large or small—is appreciated.

Together, we can build an architecture-driven platform that demonstrates how modern AI systems can support transparent, explainable and maintainable cyber investigations.
