"""Authentication configuration (ES-062).

Selects the active authenticator adapter and configures the production JWT
verifier, loaded from the environment (and an optional ``.env`` file) with an
``AUTH_`` prefix — mirroring :mod:`app.config.ai`.

``AUTH_PROVIDER`` selects the concrete authenticator behind the provider-neutral
``Authenticator`` port (the port stays technology-independent, §5; the selection
is configuration). The JWT signing secret is deliberately **not** a settings
field: it is a protected security asset consumed through the ``SecretProvider``
port (``AUTH_JWT_SECRET``, Secrets Management / ES-022), never a configuration
artifact — identical to the LLM API keys and ``DEV_AUTH_TOKEN``.
"""

from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthProviderChoice(Enum):
    """The configured concrete authenticator (closed vocabulary)."""

    DEV = "dev"
    JWT = "jwt"


class AuthSelectionSettings(BaseSettings):
    """Selects which authenticator adapter the composition root builds.

    ``AUTH_PROVIDER=dev|jwt`` — an unknown value is rejected by the closed
    enum. ``dev`` keeps the development-grade shared-token authenticator
    (ES-046, the local/test default); ``jwt`` selects the production JWT
    verifier (ES-062).
    """

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    provider: AuthProviderChoice = AuthProviderChoice.DEV


class JwtSettings(BaseSettings):
    """Production JWT verifier configuration (ES-062).

    HS256 verification only (no ``alg`` negotiation — a fixed algorithm closes
    the ``alg:none`` / downgrade attack surface). ``leeway_seconds`` absorbs
    small clock skew on ``exp``/``nbf``. ``issuer`` / ``audience`` are optional:
    when set, the token's ``iss`` / ``aud`` claim must match (a real IdP
    identifies both); when empty, the corresponding claim is not checked. The
    signing secret is not a field here — it is resolved through the
    ``SecretProvider`` (``AUTH_JWT_SECRET``).
    """

    model_config = SettingsConfigDict(
        env_prefix="AUTH_JWT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    leeway_seconds: int = 30
    issuer: str = ""
    audience: str = ""


@lru_cache
def get_auth_selection() -> AuthSelectionSettings:
    """Return the cached authenticator selection."""

    return AuthSelectionSettings()


@lru_cache
def get_jwt_settings() -> JwtSettings:
    """Return the cached JWT verifier settings instance."""

    return JwtSettings()
