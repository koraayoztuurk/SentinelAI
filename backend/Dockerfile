# syntax=docker/dockerfile:1

# SentinelAI backend — the Application deployment unit (deployment-architecture §5).
# Multi-stage, wheel-based: the builder produces a deterministic wheel artifact and
# the runtime installs only that wheel, keeping the runtime image free of build
# tooling and source layout.

# ---- builder: build the distributable wheel ----
FROM python:3.12-slim AS builder

WORKDIR /build
RUN pip install --no-cache-dir build

# Copy only what the build backend (hatchling) needs. `README.md` is referenced by
# pyproject's `readme`, so it must be present at build time.
COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m build --wheel --outdir /dist

# ---- runtime ----
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install only the built wheel (pulls the runtime dependencies; no dev extras).
COPY --from=builder /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl \
    && rm -rf /tmp/*.whl

# Run as an unprivileged user (least privilege).
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Liveness check against the container's own uvicorn over loopback (never the
# compose service name).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
