# Testing

This is the Test Foundation (ES-032) for SentinelAI. It establishes the validation
taxonomy, shared test infrastructure and coverage visibility that the specialized
validation specs build on (ES-033 Architecture Tests, ES-034 Integration Tests,
ES-035 AI Validation). It realizes the Testing Strategy (`docs/08-testing/testing-strategy.md`)
in code without prescribing a specific quality metric.

## Conventions

- Plain test functions — **no pytest fixtures** (backend) and no shared magic.
- **In-memory doubles**, deterministic inputs; no live databases or network.
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

Select a category with `pytest -m <marker>` (e.g. `pytest -m unit`). Unmarked tests
are Domain Validation. The specialized suites live at `tests/architecture/` (ES-033),
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
pytest                # tests
pytest -m unit        # a single validation category
pytest --cov=app --cov-report=term-missing   # tests + coverage report
```

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
