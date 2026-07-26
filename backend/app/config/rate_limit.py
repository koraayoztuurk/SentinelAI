"""Request-edge rate-limiting configuration (ES-068).

The request limits protecting the backend, loaded from the environment (and an
optional ``.env`` file) with a ``RATE_LIMIT_`` prefix — mirroring
:mod:`app.config.ai` and :mod:`app.config.auth`. api-design §13 keeps the
numbers out of the architecture ("rate limiting should remain configurable");
the *existence* of the limit and its 429 contract are the architectural part.

Disabled by default. Development and the test suites exercise the API without a
traffic budget, and the dev auto-sign-in demo flow would otherwise be the first
thing a limit hits; deployments turn it on (the staging/production compose
overlays do).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RateLimitSettings(BaseSettings):
    """Per-identity request limits applied at the API boundary.

    Two policies, because the surfaces differ by an order of magnitude in cost.
    The default budget covers the ordinary CRUD/read operations. The
    investigation *run* surface drives the Investigation Loop — several
    sequential provider calls under a bounded but large wall-clock budget
    (ADR-013 §1) — so a handful of concurrent runs per identity is already the
    honest ceiling, and its budget is configured separately.
    """

    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Every budget is positive: "nobody may call this" is not a rate limit, it
    # is an outage, and a deployment that wants the limiter off says so with
    # ``enabled`` rather than with a zero budget.
    enabled: bool = False
    requests: int = Field(default=120, gt=0)
    window_seconds: float = Field(default=60.0, gt=0)
    # The investigation run surface (expensive, provider-bound).
    run_requests: int = Field(default=5, gt=0)
    run_window_seconds: float = Field(default=60.0, gt=0)
    # Upper bound on tracked (identity, operation) keys, so the limiter's own
    # memory stays bounded under an identity-churning caller.
    max_tracked_keys: int = Field(default=4096, gt=0)


@lru_cache
def get_rate_limit_settings() -> RateLimitSettings:
    """Return the cached rate-limit settings instance."""

    return RateLimitSettings()
