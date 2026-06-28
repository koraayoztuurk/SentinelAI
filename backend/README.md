# SentinelAI Backend

This package contains the **backend architectural skeleton** for SentinelAI,
implemented per Engineering Specification **ES-002**.

It establishes the architectural layers, application lifecycle, configuration,
logging, shared exception infrastructure, a dependency-injection foundation and a
single operational `/health` endpoint. It intentionally contains **no business
functionality** — domain model, repositories, services, AI runtime, authentication
and database integration are owned by later specifications (ES-003 onward).

The architecture documentation under `docs/` is the single source of truth.

---

## Architecture

The backend follows a layered architecture with an inward dependency direction.
Inner layers know nothing about outer layers; the infrastructure layer implements
interfaces defined by inner layers. Configuration, core, the shared kernel and the
dependency-injection providers are cross-cutting support consumed by every layer.

```text
                HTTP request
                     │
                     ▼
        ┌─────────────────────────┐
        │      presentation/      │  thin controllers, /health, error handlers
        └─────────────┬───────────┘
                      │ depends on
                      ▼
        ┌─────────────────────────┐
        │      application/       │  application services (ADR-004) — reserved
        └─────────────┬───────────┘
                      │ depends on
                      ▼
        ┌─────────────────────────┐
        │         domain/         │  domain model — implemented (ES-003)
        └─────────────▲───────────┘
                      │ implements interfaces of
        ┌─────────────┴───────────┐
        │     infrastructure/     │  persistence & external adapters — reserved
        └─────────────────────────┘

   cross-cutting support: config/  core/  shared/  dependencies/
```

| Directory        | Responsibility                                              | Status              |
| ---------------- | ----------------------------------------------------------- | ------------------- |
| `domain/`        | Technology-independent domain model                         | Implemented (ES-003)|
| `application/`   | Application services per ADR-004                            | Reserved (ES-007–10)|
| `infrastructure/`| Persistence & external adapters                            | Reserved (ES-004–06)|
| `presentation/`  | HTTP boundary: `/health`, exception handlers               | Implemented         |
| `shared/`        | Shared kernel: base exception hierarchy                    | Implemented         |
| `core/`          | Framework core: centralized logging                        | Implemented         |
| `config/`        | Configuration management (`Settings`)                      | Implemented         |
| `dependencies/`  | FastAPI dependency-injection providers                     | Implemented         |
| `lifespan.py`    | Application startup/shutdown lifecycle                      | Implemented         |
| `main.py`        | Application factory + ASGI `app`                            | Implemented         |

---

## Getting started

Requires Python 3.12+.

```bash
cd backend
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
pip install -e ".[dev]"
```

### Run

```bash
uvicorn app.main:app --reload
```

Then check the health endpoint:

```bash
curl http://localhost:8000/health
# {"status":"ok","name":"SentinelAI","version":"0.1.0","environment":"development"}
```

### Test, lint and type-check

```bash
pytest
ruff check .
mypy app
```

---

## Configuration

Application-level configuration is read from the environment (and an optional
`.env` file) via `app/config/settings.py`:

| Variable    | Default       | Purpose                  |
| ----------- | ------------- | ------------------------ |
| `APP_NAME`  | `SentinelAI`  | Application display name |
| `APP_ENV`   | `development` | Active environment       |
| `APP_HOST`  | `0.0.0.0`     | Bind host                |
| `APP_PORT`  | `8000`        | Bind port                |
| `LOG_LEVEL` | `INFO`        | Logging level            |

Infrastructure connection settings (PostgreSQL, Neo4j, the Vector Database,
Redis, AI providers) are introduced by the specifications that own those
capabilities and are deliberately not modelled in the skeleton.
