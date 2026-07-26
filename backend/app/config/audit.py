"""Audit sink configuration (ES-069, ADR-018).

Selects the concrete audit recorder and carries the retention duration, loaded
from the environment with an ``AUDIT_`` prefix — mirroring :mod:`app.config.auth`.

Retention is configuration by decision, not by convenience: **how long** audit
records are kept is a deployment's legal question (ADR-018 §5, data-lifecycle
§3), while the existence of a retention path is architecture.
"""

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuditSinkChoice(Enum):
    """The concrete audit recorder behind the port (closed vocabulary)."""

    DURABLE = "durable"
    LOG = "log"


class AuditSettings(BaseSettings):
    """Audit sink selection and retention.

    ``durable`` is the default: the log-only recorder satisfies none of the
    §4 audit characteristics, so a deployment has to *opt out* of durability
    rather than opt in. ``log`` remains available for a deployment running
    without the authoritative store (a self-contained demo), where an
    unrecordable audit event every request would be noise rather than signal.
    """

    model_config = SettingsConfigDict(
        env_prefix="AUDIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    sink: AuditSinkChoice = AuditSinkChoice.DURABLE
    retention_days: int = Field(default=365, gt=0)


@lru_cache
def get_audit_settings() -> AuditSettings:
    """Return the cached audit settings instance."""

    return AuditSettings()
