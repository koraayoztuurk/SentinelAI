"""Tests for the correlation context (ES-031)."""

import pytest

from app.observability.correlation import Correlation, bind, current, reset

pytestmark = pytest.mark.operational


def test_bind_and_reset_restore_previous_value() -> None:
    before = current()

    token = bind(Correlation(request_id="r1", correlation_id="c1"))
    bound = current()
    assert bound is not None
    assert bound.request_id == "r1"
    assert bound.correlation_id == "c1"

    reset(token)
    assert current() is before


def test_current_is_none_without_binding() -> None:
    # Not bound in this fresh context.
    assert current() is None
