"""Tests for structured/correlated logging configuration (ES-031)."""

import json
import logging

import pytest

from app.config.settings import Settings
from app.core.logging import CorrelationFilter, JsonFormatter, configure_logging
from app.observability.correlation import Correlation, bind, reset

pytestmark = pytest.mark.operational


def _record(name: str = "app.test", msg: str = "hello") -> logging.LogRecord:
    return logging.LogRecord(name, logging.INFO, "path", 1, msg, None, None)


def test_json_formatter_emits_correlated_json() -> None:
    record = _record()
    record.request_id = "r1"
    record.correlation_id = "c1"

    data = json.loads(JsonFormatter().format(record))

    assert data["message"] == "hello"
    assert data["level"] == "INFO"
    assert data["logger"] == "app.test"
    assert data["request_id"] == "r1"
    assert data["correlation_id"] == "c1"


def test_correlation_filter_injects_or_defaults() -> None:
    log_filter = CorrelationFilter()

    unbound = _record()
    log_filter.filter(unbound)
    assert unbound.request_id == "-"
    assert unbound.correlation_id == "-"

    token = bind(Correlation(request_id="r2", correlation_id="c2"))
    try:
        bound = _record()
        log_filter.filter(bound)
        assert bound.request_id == "r2"
        assert bound.correlation_id == "c2"
    finally:
        reset(token)


def test_configure_logging_selects_format() -> None:
    try:
        configure_logging(Settings(log_format="json"))
        handler = logging.getLogger().handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)

        configure_logging(Settings(log_format="text"))
        assert not isinstance(logging.getLogger().handlers[0].formatter, JsonFormatter)

        # An invalid format falls back to text rather than blocking startup.
        configure_logging(Settings(log_format="xml"))
        assert not isinstance(logging.getLogger().handlers[0].formatter, JsonFormatter)
    finally:
        configure_logging(Settings())
