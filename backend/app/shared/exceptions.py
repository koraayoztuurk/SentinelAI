"""Shared exception infrastructure.

Defines the root of the SentinelAI exception hierarchy. Every application-defined
exception should derive from :class:`SentinelAIError`, which carries a stable
machine-readable ``code`` and a human-readable ``message``. This shape lets the
presentation layer translate failures into consistent API error responses
without leaking internal implementation details.

Only the framework-level base is defined here. Domain-specific and
service-specific exceptions are introduced by the specifications that own the
corresponding capabilities.
"""


class SentinelAIError(Exception):
    """Base class for all SentinelAI application errors.

    Attributes:
        code: A stable, machine-readable identifier for the error category.
        message: A human-readable description safe to expose to clients.
    """

    code: str = "sentinelai_error"

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        self.message = message or self.__class__.__name__
        if code is not None:
            self.code = code
        super().__init__(self.message)
