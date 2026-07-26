"""Audit sink composition (ES-069, ADR-018).

Builds the concrete recorder behind the ``AuditRecorder`` port and records the
service-lifecycle events. Both live at the composition root because they need
the persistence registry, which only exists once the application has started.

The lifecycle events matter for accountability rather than for operations: a
restart between two audited actions is part of the story those actions tell,
and the operational log that also shows it is not retention-bound evidence.
"""

import logging

from fastapi import FastAPI

from app.application.audit import (
    AuditAction,
    AuditEvent,
    AuditOutcome,
    AuditRecorder,
    LoggingAuditRecorder,
)
from app.config.audit import AuditSinkChoice, get_audit_settings
from app.infrastructure.persistence.postgres.audit import PostgresAuditRecorder
from app.infrastructure.persistence.registry import PersistenceRegistry
from app.observability import metrics

logger = logging.getLogger(__name__)


def build_audit_recorder(registry: PersistenceRegistry) -> AuditRecorder:
    """Return the configured audit recorder (``AUDIT_SINK``)."""

    if get_audit_settings().sink is AuditSinkChoice.LOG:
        logger.warning(
            "Audit sink is log-only: records are not durable, append-only or "
            "tamper-evident (AUDIT_SINK=log)"
        )
        return LoggingAuditRecorder()
    return PostgresAuditRecorder(registry.session_factory)


async def record_lifecycle_event(app: FastAPI, action: AuditAction) -> None:
    """Record a service-lifecycle audit event, contained like every other.

    A sink failure must not prevent the platform from starting or stopping
    (ADR-018 §8) — refusing to shut down because the shutdown could not be
    audited would be the clearest possible case of audit taking down the
    system it observes.
    """

    event = AuditEvent(
        action=action,
        outcome=AuditOutcome.SUCCEEDED,
        subject=None,
        identity_kind=None,
        operation=None,
        request_id=None,
    )
    try:
        await app.state.audit_recorder.record(event)
    except Exception:
        logger.exception("Audit recording failed for %s", action.value)
        metrics.record_audit_failure()
