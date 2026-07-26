"""Tests for the audit hash chain (ES-069, ADR-018 §3).

The chain is what turns "tamper-resistant" from an adjective in the
architecture into a property something can check, so these tests are written
from the attacker's side: each one alters the stored sequence the way a tamperer
would and asserts the alteration is *detected*.

Pure over its inputs — no store, no clock, no waiting.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.infrastructure.persistence.postgres.audit.chain import (
    GENESIS_HASH,
    SealedAuditRecord,
    compute_hash,
    seal,
    verify_chain,
)

pytestmark = pytest.mark.unit

_T0 = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)


def _record(
    seq: int,
    previous_hash: str,
    *,
    action: str = "operation.performed",
    subject: str | None = "analyst",
    resource: str | None = "inv-1",
    recorded_at: datetime | None = None,
) -> SealedAuditRecord:
    when = recorded_at or _T0 + timedelta(seconds=seq)
    record = SealedAuditRecord(
        seq=seq,
        action=action,
        outcome="succeeded",
        subject=subject,
        identity_kind="human",
        operation="DELETE /api/v1/investigations/inv-1",
        resource=resource,
        request_id=f"req-{seq}",
        recorded_at=when,
        previous_hash=previous_hash,
        record_hash="",
    )
    return _resealed(record)


def _resealed(record: SealedAuditRecord) -> SealedAuditRecord:
    """Return the record carrying the digest its content implies."""

    return replace(record, record_hash=seal(record))


def _chain(length: int) -> tuple[SealedAuditRecord, ...]:
    records: list[SealedAuditRecord] = []
    previous = GENESIS_HASH
    for seq in range(1, length + 1):
        record = _record(seq, previous)
        records.append(record)
        previous = record.record_hash
    return tuple(records)


# ------------------------------------------------------------------- sealing


def test_a_sealed_chain_verifies() -> None:
    result = verify_chain(_chain(5))

    assert result.valid
    assert result.checked == 5


def test_an_empty_chain_verifies() -> None:
    # Nothing recorded yet is not a broken chain.
    assert verify_chain(()).valid


def test_the_digest_covers_every_field() -> None:
    # A field left out of the digest is a field a tamperer may edit freely.
    base = dict(
        seq=1,
        action="operation.performed",
        outcome="succeeded",
        subject="analyst",
        identity_kind="human",
        operation="GET /x",
        resource="inv-1",
        request_id="req-1",
        recorded_at=_T0,
        previous_hash=GENESIS_HASH,
    )
    reference = compute_hash(**base)  # type: ignore[arg-type]
    altered = {
        "action": "investigation.erased",
        "outcome": "failed",
        "subject": "someone-else",
        "identity_kind": "system",
        "operation": "GET /y",
        "resource": "inv-2",
        "request_id": "req-2",
        "recorded_at": _T0 + timedelta(seconds=1),
        "previous_hash": "f" * 64,
        "seq": 2,
    }
    for field, value in altered.items():
        assert compute_hash(**{**base, field: value}) != reference, field  # type: ignore[arg-type]


def test_field_boundaries_cannot_be_forged() -> None:
    # Concatenating fields with a separator a value could contain would let two
    # different records seal to the same digest.
    shifted = compute_hash(
        seq=1,
        action="operation.performed",
        outcome="succeeded",
        subject="a",
        identity_kind="bc",
        operation="GET /x",
        resource=None,
        request_id="req-1",
        recorded_at=_T0,
        previous_hash=GENESIS_HASH,
    )
    original = compute_hash(
        seq=1,
        action="operation.performed",
        outcome="succeeded",
        subject="ab",
        identity_kind="c",
        operation="GET /x",
        resource=None,
        request_id="req-1",
        recorded_at=_T0,
        previous_hash=GENESIS_HASH,
    )

    assert shifted != original


# ------------------------------------------------------------------ tampering


def test_edited_content_is_detected() -> None:
    # The classic tamper: rewrite who did it, leave the digests alone.
    records = list(_chain(3))
    victim = records[1]
    records[1] = replace(victim, subject="someone-else")

    result = verify_chain(tuple(records))

    assert not result.valid
    assert result.broken_at == victim.seq
    assert result.reason is not None and "digest" in result.reason


def test_a_resealed_edit_is_still_detected() -> None:
    # The smarter tamper: edit the record *and* recompute its own digest. The
    # link from the next record is what gives it away — which is the whole
    # point of chaining rather than hashing records individually.
    records = list(_chain(3))
    records[1] = _resealed(replace(records[1], subject="someone-else"))

    result = verify_chain(tuple(records))

    assert not result.valid
    assert result.broken_at == records[2].seq
    assert result.reason is not None and "predecessor" in result.reason


def test_a_removed_record_is_detected() -> None:
    records = list(_chain(4))
    del records[2]

    result = verify_chain(tuple(records))

    assert not result.valid
    assert result.broken_at == records[2].seq


def test_reordering_is_detected() -> None:
    records = list(_chain(4))
    records[1], records[2] = records[2], records[1]

    result = verify_chain(tuple(records))

    assert not result.valid


# ------------------------------------------------------------------- retention


def test_the_retention_boundary_is_not_tampering() -> None:
    # Retention expiry removes whole records from the oldest end (ADR-018 §5).
    # The remaining head then links to something that no longer exists — an
    # expected condition, and reporting it as tampering would make the check
    # cry wolf on every deployment that keeps its retention policy.
    retained = _chain(5)[2:]

    result = verify_chain(retained)

    assert result.valid
    assert result.checked == 3