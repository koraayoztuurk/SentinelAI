"""Audit hash chain: how a record is sealed and how a sequence is verified.

The tamper-evidence mechanism of ADR-018 §3. Each record carries a digest over
its own canonical content **and** the digest of the record before it, so
altering, removing or reordering any record invalidates every digest after it.

Sealing and verification live in one module on purpose: they are two halves of
one rule, and a drift between them would silently turn every stored record
"invalid" (or, worse, make verification accept an altered one).

Deliberate properties:

- The canonical form is **explicit and positional**, with the field separator
  chosen so no field value can forge a boundary — an unambiguous encoding is the
  whole basis of the guarantee.
- ``recorded_at`` is part of the sealed content, which is why the adapter
  supplies the timestamp rather than letting the database assign it: a
  server-assigned value does not exist yet at the moment the digest is computed.
- Verification treats the earliest **retained** record's predecessor link as
  unverifiable rather than broken. Retention expiry (§5) removes whole records
  from the oldest end, so a truncated head is an expected condition, not
  tampering.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime

# Genesis link of an empty chain: a fixed, recognizable non-digest.
GENESIS_HASH = "0" * 64

# The record separator. A control character cannot occur in any field the
# recorder accepts (identifiers, enum values, request ids, ISO timestamps), so
# no value can fabricate a field boundary and re-seal as a different record.
_SEPARATOR = "\x1f"


@dataclass(frozen=True, slots=True)
class SealedAuditRecord:
    """The stored shape of an audit record: its content plus its chain links."""

    seq: int
    action: str
    outcome: str
    subject: str | None
    identity_kind: str | None
    operation: str | None
    resource: str | None
    request_id: str | None
    recorded_at: datetime
    previous_hash: str
    record_hash: str


@dataclass(frozen=True, slots=True)
class ChainVerification:
    """The outcome of verifying a retained sequence of audit records."""

    valid: bool
    checked: int
    broken_at: int | None = None
    reason: str | None = None


def compute_hash(
    *,
    seq: int,
    action: str,
    outcome: str,
    subject: str | None,
    identity_kind: str | None,
    operation: str | None,
    resource: str | None,
    request_id: str | None,
    recorded_at: datetime,
    previous_hash: str,
) -> str:
    """Return the digest sealing one record onto its predecessor."""

    fields = (
        str(seq),
        action,
        outcome,
        subject or "",
        identity_kind or "",
        operation or "",
        resource or "",
        request_id or "",
        recorded_at.isoformat(),
        previous_hash,
    )
    return hashlib.sha256(
        _SEPARATOR.join(fields).encode("utf-8")
    ).hexdigest()


def seal(record: SealedAuditRecord) -> str:
    """Recompute the digest a stored record should carry."""

    return compute_hash(
        seq=record.seq,
        action=record.action,
        outcome=record.outcome,
        subject=record.subject,
        identity_kind=record.identity_kind,
        operation=record.operation,
        resource=record.resource,
        request_id=record.request_id,
        recorded_at=record.recorded_at,
        previous_hash=record.previous_hash,
    )


def verify_chain(
    records: tuple[SealedAuditRecord, ...],
) -> ChainVerification:
    """Verify a sequence of retained records, oldest first.

    Detects content alteration (a record's digest no longer matches its
    content), removal and reordering (a record's predecessor link no longer
    matches the record before it).
    """

    previous: SealedAuditRecord | None = None
    for index, record in enumerate(records):
        if seal(record) != record.record_hash:
            return ChainVerification(
                valid=False,
                checked=index,
                broken_at=record.seq,
                reason="record content does not match its digest",
            )
        if previous is None:
            # The earliest retained record: its predecessor is either the
            # genesis link or a record removed by retention expiry. Either way
            # there is nothing left to compare against — an expected boundary.
            previous = record
            continue
        if record.previous_hash != previous.record_hash:
            return ChainVerification(
                valid=False,
                checked=index,
                broken_at=record.seq,
                reason="record does not follow its predecessor",
            )
        previous = record
    return ChainVerification(valid=True, checked=len(records))
