"""Operational environment configuration.

Defines the platform's Environment Configuration type (configuration-management
§5). ``app_env`` is a string on the environment/settings boundary; this module
turns it into the fixed, typed vocabulary of operational environments defined by
the Environment Architecture (§5) and centralizes the "non-development" distinction
so environment-aware behaviour is expressed in one place.

The vocabulary is closed (exactly four environments), so it is modelled as an enum
rather than an open string value object.
"""

from enum import StrEnum

from app.config.errors import UnknownEnvironmentError


class Environment(StrEnum):
    """The operational environments SentinelAI runs in (environment-architecture §5)."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_production_like(self) -> bool:
        """Whether this environment is anything other than development.

        Configuration that must never rely on development conveniences (for
        example insecure secret placeholders) is guarded by this single predicate
        rather than by scattered comparisons.
        """

        return self is not Environment.DEVELOPMENT


def resolve_environment(raw: str) -> Environment:
    """Resolve a raw ``app_env`` string to a typed :class:`Environment`.

    The comparison is case-insensitive and tolerant of surrounding whitespace. An
    unrecognized value raises :class:`UnknownEnvironmentError` so that a
    misconfigured environment is rejected rather than silently defaulted.
    """

    try:
        return Environment(raw.strip().lower())
    except ValueError as exc:
        raise UnknownEnvironmentError(
            f"Unknown environment '{raw}'."
        ) from exc
