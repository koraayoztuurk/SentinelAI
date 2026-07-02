"""Centralized logging configuration.

Configures the standard library logging system for the whole application so that log
formatting, level and correlation are consistent across every module.

Operational observability (ES-031): every record is annotated with the current
request's ``request_id``/``correlation_id`` (end-to-end traceability), and the output
format is selectable — human-readable ``text`` for local development or single-line
``json`` for containers/production. The format is resolved leniently here (an invalid
value falls back to ``text`` and never blocks startup, mirroring the log-level
fallback); the authoritative rejection of an invalid ``LOG_FORMAT`` is the startup
Configuration Validation.
"""

import json
import logging
from datetime import UTC, datetime

from app.config.errors import InvalidLogFormatError
from app.config.log_format import LogFormat, resolve_log_format
from app.config.settings import Settings
from app.observability.correlation import current

TEXT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] [%(request_id)s] %(message)s"


class CorrelationFilter(logging.Filter):
    """Annotates every record with the current request's correlation identifiers."""

    def filter(self, record: logging.LogRecord) -> bool:
        correlation = current()
        record.request_id = correlation.request_id if correlation else "-"
        record.correlation_id = (
            correlation.correlation_id if correlation else "-"
        )
        return True


class JsonFormatter(logging.Formatter):
    """Renders each record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        return json.dumps(payload)


def configure_logging(settings: Settings) -> None:
    """Configure application-wide logging.

    The log level is taken from :class:`~app.config.settings.Settings`; an invalid
    level falls back to ``INFO``. The output format is resolved from
    ``settings.log_format`` and falls back to ``text`` if unrecognized. A single root
    handler carries the correlation filter and the selected formatter; re-invocation
    replaces the handler rather than accumulating handlers.
    """

    level = logging.getLevelName(settings.log_level.upper())
    if not isinstance(level, int):
        level = logging.INFO

    try:
        log_format = resolve_log_format(settings.log_format)
    except InvalidLogFormatError:
        log_format = LogFormat.TEXT

    formatter: logging.Formatter = (
        JsonFormatter() if log_format is LogFormat.JSON
        else logging.Formatter(TEXT_FORMAT)
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
