# Testing

This is the Test Foundation (ES-032) for SentinelAI. It establishes the validation
taxonomy, shared test infrastructure and coverage visibility that the specialized
validation specs build on (ES-033 Architecture Tests, ES-034 Integration Tests,
ES-035 AI Validation). It realizes the Testing Strategy (`docs/08-testing/testing-strategy.md`)
in code without prescribing a specific quality metric.

## Conventions

- Plain test functions — **no pytest fixtures** (backend) and no shared magic.
- **In-memory doubles**, deterministic inputs; no live databases or network —
  except the opt-in `live` suite (below), which is the deliberate live-infrastructure
  counterpart.
- Async behaviour is exercised via `asyncio.run` (backend).
- Each architectural domain **owns its own tests** (testing-strategy §6). The shared
  support is common validation infrastructure, owned by no single domain.

## Validation taxonomy (testing-strategy §5)

Backend tests are categorized with pytest markers (registered in
`backend/pyproject.toml`; `--strict-markers` makes an unregistered marker an error):

| Marker         | Validation scope        | Notes                                             |
| -------------- | ----------------------- | ------------------------------------------------- |
| `unit`         | Domain Validation       | a component/service in isolation with doubles     |
| `integration`  | Integration Validation  | cross-domain collaboration (ES-034)               |
| `architecture` | Architecture Validation | boundaries / dependency rules (ES-033)            |
| `operational`  | Operational Validation  | health, readiness, metrics, config, startup       |
| `ai`           | AI Validation           | behavioral validation of AI capabilities (ES-035) |
| `live`         | Live-infrastructure     | real PostgreSQL required — **opt-in** (ES-040)    |
| `live_ai`      | Live AI provider        | `GOOGLE_API_KEY` + network — **opt-in** (ES-043)  |
| `live_neo4j`   | Live graph store        | real Neo4j required — **opt-in** (ES-048)         |
| `live_qdrant`  | Live vector store       | real PostgreSQL + Qdrant — **opt-in** (ES-050)    |

Select a category with `pytest -m <marker>` (e.g. `pytest -m unit`). Unmarked tests
are Domain Validation. The default run deselects the opt-in live markers (`addopts`
carries `-m "not live and not live_ai and not live_neo4j and not live_qdrant"`), so
the standard suite stays green without databases; a command-line `-m` overrides it. The specialized suites live at `tests/architecture/` (ES-033),
`tests/integration/` (ES-034), `tests/ai_validation/` (ES-035) and
`tests/operational/` (ES-036); the `operational` marker is also applied to the
health/observability/configuration suites.

The frontend uses Vitest + React Testing Library; its categories are expressed by
directory/naming (e.g. component tests next to components, page/integration tests
under `pages/`), plus the shared scaffold in `src/test/` (`setup.ts`, `TestQueryProvider`).

## Shared support (backend)

Reusable validation infrastructure lives under `backend/tests/support/` — import it
from any test (it is not collected as tests):

- `tests/support/doubles.py` — in-memory repository doubles for the Investigation
  family plus the Graph and Memory repositories (ES-034), and the deterministic
  `SequentialIdGenerator` / `FixedClock`.
- `tests/support/builders.py` — pure, immutable builders (`build_investigation`,
  `build_evidence`, `build_finding`, `build_report`, `build_entity`,
  `build_relationship`, `build_memory_item`) and the service factories
  (`make_investigation_service()`, `make_graph_service()`, `make_memory_service()`).

`tests/foundation/test_support.py` exercises this support. The integration suite
(`tests/integration/`, marked `integration`, ES-034) reuses it rather than
re-defining doubles.

## Running

Backend (from `backend/`):

```bash
ruff check .          # lint
mypy app              # types (strict)
pytest                # tests (live suite deselected)
pytest -m unit        # a single validation category
pytest --cov=app --cov-report=term-missing   # tests + coverage report
```

### Live PostgreSQL suite (opt-in)

The `live` suite (`backend/tests/live/`) verifies the concrete PostgreSQL
adapters and the Alembic migrations against a real database. Locally:

```bash
docker compose --profile data up -d postgres   # publishes 127.0.0.1:5432
cd backend
POSTGRES_HOST=127.0.0.1 pytest -m live         # PowerShell: $env:POSTGRES_HOST="127.0.0.1"; pytest -m live
```

Use `127.0.0.1` rather than `localhost`: on Windows, `localhost` resolves to
IPv6 first, and the published port listens on IPv4 only — the extra `::1`
connection attempt costs seconds per fresh connect.

The connection comes from the standard `POSTGRES_*` environment variables
(`app.config.database.PostgresSettings`). The tests migrate the database to the
Alembic head and truncate the tables they touch, so the target database is
disposable. CI runs the suite in the `backend-live` job against a PostgreSQL
service container.

### Live Neo4j suite (opt-in)

The `live_neo4j` suite (`backend/tests/live/test_neo4j_graph.py`) verifies the
concrete Neo4j graph adapter and the schema migration against a real graph
store. Locally:

```bash
docker compose --profile data up -d neo4j   # publishes 127.0.0.1:7687
cd backend
# PowerShell: $env:NEO4J_URI="bolt://127.0.0.1:7687"; $env:NEO4J_PASSWORD="<compose pw>"; pytest -m live_neo4j
NEO4J_URI=bolt://127.0.0.1:7687 NEO4J_PASSWORD=<compose pw> pytest -m live_neo4j
```

Both the host-run tests **and** the app under test read the standard `NEO4J_*`
variables (`app.config.database.Neo4jSettings`), so a single pair of overrides
configures everything: `NEO4J_URI` (the compose default URI uses the
compose-internal hostname, unreachable from the host) and `NEO4J_PASSWORD` (to
match the compose password). The tests bootstrap the graph schema and clear
their nodes, so the target graph is disposable. Neo4j 5 rejects passwords under
8 characters; the dev compose relaxes that policy so short local passwords work.
CI runs the suite in the `backend-live-neo4j` job against a Neo4j service
container.

### Live Qdrant suite (opt-in)

The `live_qdrant` suite (`backend/tests/live/test_memory_outbox_qdrant.py`)
verifies the transactional outbox → idempotent projector → vector store pipeline
(ADR-012) against a real PostgreSQL **and** a real Qdrant, with a **fake
deterministic embedder** (no provider key — CI-able). Locally:

```bash
docker compose --profile data up -d postgres qdrant   # publishes 127.0.0.1:5432 + 6333
cd backend
# PowerShell: $env:POSTGRES_HOST="127.0.0.1"; $env:QDRANT_URL="http://127.0.0.1:6333"; pytest -m live_qdrant
POSTGRES_HOST=127.0.0.1 QDRANT_URL=http://127.0.0.1:6333 pytest -m live_qdrant
```

The tests migrate PostgreSQL to head, truncate the memory tables and drop the
Qdrant collection, so both stores are disposable. CI runs the suite in the
`backend-live-qdrant` job against PostgreSQL + Qdrant service containers.

### Live AI suite (opt-in)

`pytest -m live_ai` exercises the real Gemini provider: the adapter smoke test
(one `generate` call) and the full Investigation Loop run over the live stack
(also needs the PostgreSQL above). Tests read `GOOGLE_API_KEY` from the
environment, falling back to the repository-root `.env`; without a key they
skip. These tests call the external provider and are never part of CI.

Frontend (from `frontend/`):

```bash
npm run lint
npm run typecheck
npm run test
npm run test:coverage   # tests + coverage report
npm run build
```

## Coverage

Coverage is **measured and reported, never gated** — quality confidence here is
architectural assurance, not a coverage percentage (testing-strategy §7/§8). Reports
are written to fixed paths: `backend/htmlcov/` (pytest-cov, HTML) and
`frontend/coverage/` (Vitest v8, HTML). CI publishes both as build artifacts and adds
no threshold.
