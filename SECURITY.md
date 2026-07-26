# Security Policy

SentinelAI is a cyber-investigation platform: the data it holds is, by nature,
sensitive. Vulnerability reports are welcome and taken seriously.

---

## Reporting a Vulnerability

**Use GitHub's private vulnerability reporting** — on this repository, open the
**Security** tab and choose **Report a vulnerability**. The report stays private
between you and the maintainer until a fix is published.

**Please do not open a public issue, pull request or discussion for a security
problem.** A public report is a disclosure, and it exposes every deployment
before a fix exists.

A useful report includes:

- what the vulnerability allows an attacker to do, and under which trust
  boundary (`docs/07-security/security-architecture.md` §4 names them)
- the affected version — a release tag, or the commit sha the platform status
  surface reports
- reproduction steps, or the request sequence that triggers it
- the configuration it requires (authentication provider, environment,
  multi-tenancy on or off)

If you are unsure whether something is a vulnerability, report it privately
anyway. Deciding that is the maintainer's job, not yours.

---

## What to Expect

This project has **one maintainer, no on-call rotation and no security team**, so
the honest commitment is *best effort, in good faith*, not a service level:

- your report is acknowledged as soon as it is seen
- you get an assessment — accepted, needs more information, or out of scope —
  with the reasoning
- an accepted report is fixed, and the fix is released with an advisory that
  credits you unless you ask otherwise
- the advisory is published **after** the fix, so deployments can upgrade before
  the details are public

There is no bug bounty. Nothing in this policy is a contractual promise.

---

## Scope

**In scope** — anything in this repository that runs:

- the backend application, its API surface and its authorization boundaries
- the frontend application
- the deployment definitions (compose overlays, edge configuration) and the CI
  pipeline that builds and publishes images

**Out of scope**, with reasons rather than dismissals:

- **Third-party dependency vulnerabilities.** Report them upstream. The image
  pipeline scans every build and fails on fixable CRITICAL/HIGH findings
  (`infrastructure/README.md`); an unfixed upstream finding is triaged, not
  hidden. If a dependency issue is *exploitable through this platform in a way
  the upstream report does not cover*, that is in scope — say so in the report.
- **The development authentication provider (`AUTH_PROVIDER=dev`).** It is a
  shared-secret, development-grade authenticator, documented as such
  (`docs/07-security/authentication-authorization.md`), and it fails startup
  outside development without its secret. Running it in production is a
  deployment error, not a platform vulnerability.
- **Anything already recorded as a Known Gap** in the architecture
  documentation — for example the untenanted shared-knowledge layer, the absent
  audit query surface, or backup/restore interaction with erasure. These are
  documented limitations with a stated governance path; a report that they exist
  tells us what we already published. A report that one of them is *worse than
  documented* is in scope and valuable.
- **Findings that assume the attacker already has what they are trying to
  reach** — direct database access, the deployment's secrets, or the host.
- **Missing hardening with no exploit path**, unless you can describe the attack
  it enables.

---

## Supported Versions

The platform is **pre-1.0**: only the latest release and the current `main`
branch receive fixes. There are no maintained release branches, and no backports.

| Version | Supported |
|---|---|
| `main` | ✅ |
| Latest release | ✅ |
| Anything earlier | ❌ — upgrade |

---

## Verifying What You Run

Published images are signed and carry an SBOM and build provenance, so a
deployment can prove that what it runs is what the pipeline produced. The
verification commands are in
[`infrastructure/README.md`](infrastructure/README.md).

Deployments follow **digests**, not tags (ADR-021): a tag can be re-pointed
after it was verified.
