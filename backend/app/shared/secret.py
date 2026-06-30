"""Secret protection primitive.

A :class:`Secret` wraps a sensitive string so that it cannot leak accidentally
through logging, representation or tracebacks (Secrets Management: confidentiality
by default, least exposure; secrets are never logged). The value is hidden and its
``repr``/``str`` are masked; the only way to read it is the explicit
:meth:`Secret.reveal`.

This is a technology-independent, cross-cutting kernel primitive (the platform's own
equivalent of ``pydantic.SecretStr``), so it lives in the shared kernel and may be
consumed by any layer. It is deliberately a hand-written class rather than a frozen
dataclass so the value stays hidden and the masked representations can be enforced.
"""

_MASK = "********"


class Secret:
    """An opaque, masked holder for a sensitive string value."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        """Return the underlying secret value.

        This is the single, explicit access point to the protected value. It is
        expected to be called only by the adapter/provider layers that actually
        consume the secret (for example to authenticate to an external system);
        other code should pass the :class:`Secret` around without revealing it
        (least exposure).
        """

        return self._value

    def __repr__(self) -> str:
        return f"Secret({_MASK})"

    def __str__(self) -> str:
        return _MASK

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Secret) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)
