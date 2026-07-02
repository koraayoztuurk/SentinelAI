"""Log output format configuration.

Defines the fixed vocabulary of log output formats (Platform Configuration). Like
the operational :class:`~app.config.environment.Environment`, ``log_format`` is a
string on the settings boundary that is resolved to this typed, closed enum; an
unrecognized value is rejected fail-fast by the Configuration Validation.
"""

from enum import StrEnum

from app.config.errors import InvalidLogFormatError


class LogFormat(StrEnum):
    """The supported log output formats."""

    TEXT = "text"
    JSON = "json"


def resolve_log_format(raw: str) -> LogFormat:
    """Resolve a raw ``log_format`` string to a typed :class:`LogFormat`.

    Case-insensitive and whitespace-tolerant. An unrecognized value raises
    :class:`InvalidLogFormatError`.
    """

    try:
        return LogFormat(raw.strip().lower())
    except ValueError as exc:
        raise InvalidLogFormatError(f"Unknown log format '{raw}'.") from exc
