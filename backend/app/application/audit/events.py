"""Audit event model.

An audit event is the architectural record of a security-relevant activity
(audit-and-observability.md §4): it captures who acted, on which resource, with
what outcome, and carries the request identifier for traceability. The chronological
``when`` is added by the recorder/sink. These are AI-neutral application-layer
structures; the closed ``AuditAction``/``AuditOutcome`` enumerations keep the
recorded vocabulary type-safe.
"""

from dataclasses import dataclass
from enum import Enum


class AuditAction(Enum):
    """The kind of audited activity."""

    OPERATION_PERFORMED = "operation.performed"
    AUTHENTICATION_FAILED = "authentication.failed"
    AUTHORIZATION_DENIED = "authorization.denied"


class AuditOutcome(Enum):
    """The outcome recorded for an audited activity."""

    SUCCEEDED = "succeeded"
    DENIED = "denied"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """A single security-relevant audit record."""

    action: AuditAction
    outcome: AuditOutcome
    subject: str | None
    identity_kind: str | None
    operation: str | None
    request_id: str
