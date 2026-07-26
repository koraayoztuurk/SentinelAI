# Deployment infrastructure (ES-068)

Concrete deployment artifacts for the environments defined by
`docs/06-devops/environment-architecture.md`. The normative documents stay
technology-independent; the operational specifics live here.

```
infrastructure/
  nginx/edge.conf   # staging/production edge: TLS, security headers, limits
  tls/              # certificate + key, mounted read-only (never committed)
```

---

## Registry and image naming

| | |
|---|---|
| Registry | `ghcr.io` (GitHub Container Registry) |
| Backend image | `ghcr.io/<owner>/sentinelai-backend` |
| Frontend image | `ghcr.io/<owner>/sentinelai-frontend` |
| Published by | `.github/workflows/ci.yml`, job `images` |
| Authentication | the workflow's `GITHUB_TOKEN` (`packages: write`) — no long-lived registry credential exists |

GHCR names must be lowercase; the repository owner already is.

### Tags

| Trigger | Tags |
|---|---|
| push to `main` | `latest`, `main`, `sha-<full-sha>` |
| push of tag `vX.Y.Z` | `X.Y.Z`, `X.Y`, `sha-<full-sha>` |
| pull request | none — the image is built and scanned, never published |

`sha-<full-sha>` is the identity that matters operationally: it names exactly one
build. `latest` is a convenience for a demo environment, not something a
production deployment should follow — pin `X.Y.Z` or the sha.

### Supply chain

Every published image carries, and every build proves:

- **Vulnerability scan** (Trivy). Reported at CRITICAL/HIGH/MEDIUM as a run
  artifact; the build *fails* only on a **fixable** CRITICAL/HIGH. An unfixed
  upstream base-image finding is triaged (rebuild on a newer base when one
  ships), never a permanent block on a fix we cannot make.
- **SBOM** — SPDX, attached to the image as a buildx attestation and uploaded as
  a run artifact.
- **Provenance** — SLSA provenance (`mode=max`) attached to the image.
- **Signature** — cosign keyless, bound to the workflow's OIDC identity. No
  signing key exists to leak.

Verify a published image:

```bash
cosign verify ghcr.io/<owner>/sentinelai-backend:<tag> \
  --certificate-identity-regexp "https://github.com/<owner>/SentinelAI/.github/workflows/ci.yml@.*" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

---

## Promotion (ES-072, ADR-021)

CI publishes a **candidate**. Deciding to run one is a separate, authorized act —
`.github/workflows/promote.yml` (manual dispatch: version + target environment).

The workflow resolves the requested version to a **digest** per unit, verifies
the cosign signature and the presence of the SBOM and provenance attestations
**before** anything is deployed, and emits a digest-pinned pair:

```env
BACKEND_IMAGE=ghcr.io/<owner>/sentinelai-backend@sha256:<digest>
FRONTEND_IMAGE=ghcr.io/<owner>/sentinelai-frontend@sha256:<digest>
```

That file (`promotion.env`, published as a run artifact) is what an environment
consumes — the overlays already read those two variables:

```bash
docker compose --env-file promotion.env -f docker-compose.yml \
  -f docker-compose.staging.yml --profile data up -d
```

Deployments follow **digests, not tags**: a tag can be re-pointed after it was
verified, so a tag-following deployment cannot know what it is running.

The workflow **stops at the verified, pinned, recorded pair** — it does not
deploy, because no environment is hosted. Two things are deployment
configuration rather than repository content, and without them the mechanism has
no gate:

| Setting | Where | Why it matters |
|---|---|---|
| Environment protection with a required reviewer, for `staging` and `production` | repository → Settings → Environments | This is the authorization step (release-management §5a). An environment with no reviewer promotes without approval. |
| Private vulnerability reporting | repository → Settings → Security | The channel `SECURITY.md` publishes only exists once it is enabled. |

---

## Environment targets

| Environment | Compose invocation | Notes |
|---|---|---|
| Development | `docker compose up --build` | local build, no TLS, rate limiting off |
| Staging | `docker compose -f docker-compose.yml -f docker-compose.staging.yml --profile data up -d` | published image, TLS edge, JSON debug logs |
| Production | `docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile data up -d` | published image, TLS edge, hardened + bounded |

The staging and production overlays **pull** (`pull_policy: always`); they do not build. Until
CI has published an image for the tag you select, those commands fail by design — a deployment
runs the artifact that was scanned and signed, not one compiled on the deployment host. They also
need **Docker Compose ≥ 2.24** for the `!override` / `!reset` merge tags.

Select the version with `BACKEND_IMAGE` / `FRONTEND_IMAGE`:

```bash
BACKEND_IMAGE=ghcr.io/<owner>/sentinelai-backend:1.4.0 \
FRONTEND_IMAGE=ghcr.io/<owner>/sentinelai-frontend:1.4.0 \
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile data up -d
```

**Promotion between environments is not automated.** CI delivers a verified
artifact; deciding that a given artifact may enter an environment is release
governance and belongs to Milestone H (release-management §5, "controlled
release progression"). Today that decision is the owner's, executed by running
the command above with a chosen tag.

### What the overlays change

Both non-development overlays run the published image (`pull_policy: always`),
terminate TLS at `infrastructure/nginx/edge.conf`, drop all Linux capabilities,
forbid privilege escalation, mount the backend root filesystem read-only, bound
CPU/memory, bound log growth, and enable the request-edge rate limiting
(`RATE_LIMIT_ENABLED=true`). Production additionally stops publishing the data
tier's loopback ports — those exist only so a developer's opt-in live suites can
reach the stores.

Staging differs from production only where its *operational responsibility*
differs (environment-architecture §5): `APP_ENV=staging`, JSON logs at DEBUG,
smaller resource bounds.

---

## TLS material

The edge expects:

```
infrastructure/tls/fullchain.pem
infrastructure/tls/privkey.pem
```

mounted read-only into the frontend container at `/etc/nginx/tls`. They are
deployment secrets (`docs/07-security/secrets-management.md`): git-ignored, and
provisioned on the deployment host — from the organization's CA, or from Let's
Encrypt with the renewed files landing at those paths and `docker compose exec
frontend nginx -s reload` afterwards.

For a local trial of the production shape, a self-signed pair is enough (the
browser will warn, which is correct — it is not a trusted certificate):

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout infrastructure/tls/privkey.pem \
  -out infrastructure/tls/fullchain.pem \
  -subj "/CN=localhost"
```

---

## Edge behaviour worth knowing

- **`client_max_body_size 10m`** is aligned with `EVIDENCE_PAYLOAD_MAX_BYTES`
  (ADR-015). Raising the application bound without raising this one turns a
  clean `413` from the API into a rejection at the edge.
- **The run surface gets its own 600s proxy timeout.** An investigation run
  makes several sequential provider calls, each with its own bound (ADR-013 §1);
  the rest of the API keeps a 60s timeout. If `RUN_CYCLE_BUDGET` or the provider
  timeouts grow, this must grow with them.
- **`limit_req` protects against anonymous floods**, which the application
  cannot: the backend's limiter is per authenticated identity (api-design §13).
  The two layers are complementary, not redundant.
- **`/metrics` and `/health/ready` return 404 at the edge.** They describe the
  deployment rather than the product; a scraper or orchestrator reaches the
  backend directly on the internal network.
- **Security headers are not repeated per `location`** — nginx inherits
  `add_header` from an outer level only while the inner level declares none, so
  the asset block deliberately uses `expires` instead of an `add_header`.
