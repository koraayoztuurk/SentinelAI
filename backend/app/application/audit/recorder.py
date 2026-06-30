"""Audit recorder contract.

Audit recording is owned by the Application Domain (audit-and-observability.md §6).
This module defines the provider-neutral recorder port; the concrete durable,
tamper-resistant store (with retention and non-repudiation guarantees) is deferred.

The default :class:`LoggingAuditRecorder` writes audit events to a dedicated
``audit`` logger so accountability works end to end, while the durable store remains
a later concern. Audit records never include credentials or secrets.
"""

import logging
from typing import Protocol

from app.application.audit.events import AuditEvent

_audit_logger = logging.getLogger("audit")


class AuditRecorder(Protocol):
    """Replaceable port that records audit events."""

    async def record(self, event: AuditEvent) -> None: ...


class LoggingAuditRecorder:
    """Default recorder that emits audit events to the ``audit`` logger.

    The durable, tamper-resistant audit store is deferred; this keeps the audit
    capability observable in the meantime.
    """

    async def record(self, event: AuditEvent) -> None:
        _audit_logger.info(
            "audit action=%s outcome=%s subject=%s identity_kind=%s "
            "operation=%s request_id=%s",
            event.action.value,
            event.outcome.value,
            event.subject,
            event.identity_kind,
            event.operation,
            event.request_id,
        )
