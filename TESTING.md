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

Select a category with `pytest -m <marker>` (e.g. `pytest -m unit`). Unmarked tests
are Domain Validation. The default run deselects `live` (`addopts` carries
`-m "not live"`), so the standard suite stays green without databases; a
command-line `-m` overrides it. The specialized suites live at `tests/architecture/` (ES-033),
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
