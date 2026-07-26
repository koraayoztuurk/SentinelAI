"""Audit event model.

An audit event is the architectural record of a security-relevant activity
(audit-and-observability.md §4): it captures who acted, on which resource, with
what outcome, and carries the request identifier for traceability. The chronological
``when`` is added by the recorder/sink. These are AI-neutral application-layer
structures; the closed ``AuditAction``/``AuditOutcome`` enumerations keep the
recorded vocabulary type-safe.

The vocabulary spans the §4 categories the platform actually acts in and carries
**no value that nothing emits** (ADR-018 §7): a placeholder for an activity the
platform cannot perform would assert accountability it does not have. The §4
*administrative* category is therefore unrepresented until an administrative
surface exists.

An audit record holds **identifiers, not content** (ADR-018 §6). That is what
makes the audit exception defensible — audit records survive the erasure they
document (data-lifecycle.md §5), and they can, because there is no title,
evidence body or knowledge text in them to erase.
"""

from dataclasses import dataclass
from enum import Enum


class AuditAction(Enum):
    """The kind of audited activity (closed vocabulary, ADR-018 §7)."""

    # Identity activities (§4).
    AUTHENTICATION_FAILED = "authentication.failed"
    # Authorization activities (§4).
    AUTHORIZATION_DENIED = "authorization.denied"
    # The generic protected-operation record.
    OPERATION_PERFORMED = "operation.performed"
    # Investigation activities (§4): erasure is recorded as an erasure rather
    # than as an anonymous operation — data-lifecycle.md §5 requires the record
    # of *who erased what* to outlive the erased data (the ES-064 deferral).
    INVESTIGATION_ERASED = "investigation.erased"
    # System activities (§4): security-policy enforcement and the service
    # lifecycle, so a refusal or a restart is visible in the audit record
    # rather than only in operational logs.
    TRAFFIC_LIMIT_ENFORCED = "traffic.limit_enforced"
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"


class AuditOutcome(Enum):
    """The outcome recorded for an audited activity."""

    SUCCEEDED = "succeeded"
    DENIED = "denied"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """A single security-relevant audit record.

    ``resource`` identifies the affected object (an investigation, a memory
    item, a graph entity) — an **identifier**, never its content. It is absent
    for activities that address no particular resource, such as a failed
    authentication or a service lifecycle event.

    ``request_id`` is absent for the same reason on activities that are not
    requests at all: a service start has no correlation to carry, and
    fabricating one would make an unrelated record look traceable.
    """

    action: AuditAction
    outcome: AuditOutcome
    subject: str | None
    identity_kind: str | None
    operation: str | None
    request_id: str | None
    resource: str | None = None
