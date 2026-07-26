"""Tests for startup secret availability (ES-069, secrets-management §6).

An absent secret is a configuration failure, not a runtime one: outside
development a deployment that cannot perform the capabilities it is configured
for must not enter service. Development keeps lazy resolution so a partially
configured environment stays workable.

The required set is *derived from configuration*, so most of these tests are
about that derivation — requiring the wrong secret would refuse a startup that
should succeed, which is worse than the gap it closes.
"""

import pytest

from app.application.secrets import SecretName, SecretNotFoundError
from app.config.ai import LLMProviderChoice, LLMSelectionSettings
from app.config.auth import AuthProviderChoice, AuthSelectionSettings
from app.config.environment import Environment
from app.config.errors import MissingSecretError
from app.config.settings import Settings
from app.config.validation import (
    required_secret_names,
    validate_secret_availability,
)
from app.shared.secret import Secret

pytestmark = pytest.mark.operational


class _Secrets:
    """Secret provider double over an explicit mapping."""

    def __init__(self, **values: str) -> None:
        self._values = values

    def resolve(self, name: SecretName) -> Secret:
        try:
            return Secret(self._values[name.value])
        except KeyError as exc:
            raise SecretNotFoundError(f"'{name.value}' is not available.") from exc


def _names(
    *,
    auth: AuthProviderChoice = AuthProviderChoice.DEV,
    llm: LLMProviderChoice = LLMProviderChoice.GEMINI,
    fallback: LLMProviderChoice | None = None,
    projector: bool = True,
) -> set[str]:
    required = required_secret_names(
        Settings(outbox_projector_enabled=projector),
        AuthSelectionSettings(provider=auth),
        LLMSelectionSettings(provider=llm, fallback_provider=fallback),
    )
    return {name.value for name in required}


# ------------------------------------------------------------------ derivation


def test_the_selected_authenticator_decides_which_auth_secret_is_required() -> None:
    assert "DEV_AUTH_TOKEN" in _names(auth=AuthProviderChoice.DEV)
    assert "AUTH_JWT_SECRET" not in _names(auth=AuthProviderChoice.DEV)
    assert "AUTH_JWT_SECRET" in _names(auth=AuthProviderChoice.JWT)
    assert "DEV_AUTH_TOKEN" not in _names(auth=AuthProviderChoice.JWT)


def test_the_fallback_provider_s_key_is_required_too() -> None:
    # A fallback that cannot authenticate is not a fallback (ES-067).
    assert "NVIDIA_API_KEY" not in _names(llm=LLMProviderChoice.GEMINI)
    assert "NVIDIA_API_KEY" in _names(
        llm=LLMProviderChoice.GEMINI, fallback=LLMProviderChoice.NVIDIA
    )


def test_the_embedding_key_is_required_while_the_projector_runs() -> None:
    # Embedding stays on Gemini regardless of the LLM selection (ES-050), so
    # an NVIDIA-only deployment still needs the Google key — unless it is not
    # deriving embeddings at all.
    assert "GOOGLE_API_KEY" in _names(llm=LLMProviderChoice.NVIDIA)
    assert "GOOGLE_API_KEY" not in _names(
        llm=LLMProviderChoice.NVIDIA, projector=False
    )


def test_an_optional_provider_key_is_not_required() -> None:
    # NVD's own contract makes the key optional (keyless access is merely
    # rate-limited harder), so requiring it would refuse a startup over a
    # capability that works without it.
    assert "NVD_API_KEY" not in _names()


def test_no_secret_is_required_twice() -> None:
    names = required_secret_names(
        Settings(outbox_projector_enabled=True),
        AuthSelectionSettings(provider=AuthProviderChoice.DEV),
        LLMSelectionSettings(provider=LLMProviderChoice.GEMINI),
    )

    assert len(names) == len(set(names))


# ------------------------------------------------------------------ enforcement


def test_development_stays_lazy() -> None:
    # A developer must be able to exercise the capabilities they configured
    # without providing the ones they did not.
    validate_secret_availability(
        Environment.DEVELOPMENT,
        _Secrets(),
        (SecretName("GOOGLE_API_KEY"),),
    )


@pytest.mark.parametrize(
    "environment",
    [Environment.TEST, Environment.STAGING, Environment.PRODUCTION],
)
def test_a_missing_secret_prevents_startup_outside_development(
    environment: Environment,
) -> None:
    with pytest.raises(MissingSecretError) as raised:
        validate_secret_availability(
            environment, _Secrets(), (SecretName("AUTH_JWT_SECRET"),)
        )

    assert raised.value.secret_names == ("AUTH_JWT_SECRET",)


def test_a_present_secret_passes() -> None:
    validate_secret_availability(
        Environment.PRODUCTION,
        _Secrets(AUTH_JWT_SECRET="s3cret"),
        (SecretName("AUTH_JWT_SECRET"),),
    )


def test_a_blank_secret_counts_as_missing() -> None:
    # An empty variable is how an unset secret usually looks in a container.
    with pytest.raises(MissingSecretError):
        validate_secret_availability(
            Environment.PRODUCTION,
            _Secrets(AUTH_JWT_SECRET="   "),
            (SecretName("AUTH_JWT_SECRET"),),
        )


def test_every_missing_secret_is_reported_at_once() -> None:
    # Fixing a misconfiguration one restart at a time is its own outage.
    with pytest.raises(MissingSecretError) as raised:
        validate_secret_availability(
            Environment.PRODUCTION,
            _Secrets(GOOGLE_API_KEY="k"),
            (
                SecretName("AUTH_JWT_SECRET"),
                SecretName("GOOGLE_API_KEY"),
                SecretName("NVIDIA_API_KEY"),
            ),
        )

    assert raised.value.secret_names == ("AUTH_JWT_SECRET", "NVIDIA_API_KEY")


def test_the_error_names_the_secret_but_never_its_value() -> None:
    with pytest.raises(MissingSecretError) as raised:
        validate_secret_availability(
            Environment.PRODUCTION,
            _Secrets(AUTH_JWT_SECRET=""),
            (SecretName("AUTH_JWT_SECRET"),),
        )

    message = str(raised.value)
    assert "AUTH_JWT_SECRET" in message
    assert raised.value.code == "config.missing_secret"
