"""Tests for the secrets foundation (ES-022).

Verifies that ``Secret`` never leaks its value through representation, that the
environment provider resolves and protects secrets, and that a missing secret is
reported as ``SecretNotFoundError``.
"""

import os

import pytest

from app.application.secrets import SecretName, SecretNotFoundError
from app.infrastructure.secrets import EnvironmentSecretProvider
from app.shared.secret import Secret

# ------------------------------------------------------------------------ secret


def test_secret_masks_value_in_representation() -> None:
    secret = Secret("s3cr3t")
    assert repr(secret) == "Secret(********)"
    assert str(secret) == "********"
    assert "s3cr3t" not in repr(secret)
    assert "s3cr3t" not in str(secret)


def test_secret_reveal_returns_value() -> None:
    assert Secret("s3cr3t").reveal() == "s3cr3t"


def test_secret_equality_and_hash() -> None:
    assert Secret("a") == Secret("a")
    assert Secret("a") != Secret("b")
    assert Secret("a") != "a"
    assert hash(Secret("a")) == hash(Secret("a"))


# --------------------------------------------------------------------- secret name


def test_secret_name_value() -> None:
    assert SecretName("OPENAI_API_KEY").value == "OPENAI_API_KEY"


def test_blank_secret_name_rejected() -> None:
    with pytest.raises(ValueError):
        SecretName("  ")


# ----------------------------------------------------------------- env provider


def test_environment_provider_resolves_secret() -> None:
    os.environ["TEST_SECRET_VALUE"] = "v"
    try:
        secret = EnvironmentSecretProvider().resolve(SecretName("TEST_SECRET_VALUE"))
        assert secret.reveal() == "v"
    finally:
        del os.environ["TEST_SECRET_VALUE"]


def test_environment_provider_missing_secret_raises() -> None:
    os.environ.pop("ABSENT_SECRET", None)
    with pytest.raises(SecretNotFoundError):
        EnvironmentSecretProvider().resolve(SecretName("ABSENT_SECRET"))


def test_environment_provider_empty_secret_raises() -> None:
    os.environ["EMPTY_SECRET"] = ""
    try:
        with pytest.raises(SecretNotFoundError):
            EnvironmentSecretProvider().resolve(SecretName("EMPTY_SECRET"))
    finally:
        del os.environ["EMPTY_SECRET"]


def test_secret_not_found_error_code() -> None:
    assert SecretNotFoundError.code == "secret.not_found"
