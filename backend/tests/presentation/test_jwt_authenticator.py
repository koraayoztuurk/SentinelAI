"""Tests for the production JWT authenticator (ES-062).

Deterministic, credential-free verification: a well-formed HS256 token yields
the identity; expiry, not-yet-valid, bad signature, malformed structure,
missing subject/expiry, an unsupported (or ``none``) algorithm, and an
unaccepted issuer/audience all raise ``AuthenticationError`` (→ 401); the
signing secret comes from the SecretProvider and never appears in an error.
Plain functions, ``asyncio.run``, a lightweight fake request.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from app.application.secrets import SecretName, SecretNotFoundError
from app.config.auth import JwtSettings
from app.presentation.api.auth import IdentityKind
from app.presentation.api.errors import AuthenticationError
from app.presentation.api.jwt_authenticator import JwtAuthenticator
from app.shared.secret import Secret
from tests.support.jwt import mint_jwt

_SECRET = "jwt-test-signing-secret-2f9a"


class _FixedSecrets:
    def resolve(self, name: SecretName) -> Secret:
        assert name == SecretName("AUTH_JWT_SECRET")
        return Secret(_SECRET)


class _EmptySecrets:
    def resolve(self, name: SecretName) -> Secret:
        raise SecretNotFoundError(f"Secret '{name}' is not configured.")


class _FakeRequest:
    """A minimal stand-in exposing only what the authenticator reads."""

    def __init__(self, authorization: str | None) -> None:
        self.headers = (
            {"Authorization": authorization} if authorization is not None else {}
        )


def _authenticator(
    secrets: object = None,
    *,
    now: datetime | None = None,
    issuer: str = "",
    audience: str = "",
    leeway: int = 30,
) -> JwtAuthenticator:
    return JwtAuthenticator(
        JwtSettings(leeway_seconds=leeway, issuer=issuer, audience=audience),
        secrets if secrets is not None else _FixedSecrets(),
        now=(lambda: now) if now is not None else None,
    )


def _authenticate(auth: JwtAuthenticator, token: str | None):  # type: ignore[no-untyped-def]
    header = f"Bearer {token}" if token is not None else None
    return asyncio.run(auth.authenticate(_FakeRequest(header)))


# ----------------------------------------------------------------- happy path


def test_valid_token_yields_the_identity() -> None:
    token = mint_jwt(_SECRET, "analyst-erin", kind="human")
    identity = _authenticate(_authenticator(), token)

    assert identity.subject == "analyst-erin"
    assert identity.kind is IdentityKind.HUMAN


def test_kind_claim_maps_to_identity_kind() -> None:
    token = mint_jwt(_SECRET, "svc-ingest", kind="system")
    assert _authenticate(_authenticator(), token).kind is IdentityKind.SYSTEM


def test_absent_kind_defaults_to_human() -> None:
    token = mint_jwt(_SECRET, "analyst-1", extra_claims={"kind": None})
    # A null kind falls back to the default rather than failing.
    with pytest.raises(AuthenticationError):
        _authenticate(_authenticator(), token)


# --------------------------------------------------------------- rejections


def test_expired_token_is_rejected() -> None:
    token = mint_jwt(_SECRET, "analyst-1", expires_in=-3600)
    with pytest.raises(AuthenticationError) as exc:
        _authenticate(_authenticator(), token)
    assert "expired" in str(exc.value).lower()


def test_not_yet_valid_token_is_rejected() -> None:
    future = int(datetime.now(UTC).timestamp()) + 3600
    token = mint_jwt(_SECRET, "analyst-1", not_before=future)
    with pytest.raises(AuthenticationError):
        _authenticate(_authenticator(), token)


def test_tampered_signature_is_rejected_without_leaking_the_secret() -> None:
    token = mint_jwt(_SECRET, "analyst-1")
    forged = mint_jwt("attacker-secret", "analyst-1")
    # Same header/payload region, different signature.
    tampered = token.rsplit(".", 1)[0] + "." + forged.rsplit(".", 1)[1]
    with pytest.raises(AuthenticationError) as exc:
        _authenticate(_authenticator(), tampered)
    assert _SECRET not in str(exc.value)


def test_alg_none_downgrade_is_rejected() -> None:
    token = mint_jwt(_SECRET, "analyst-1", algorithm="none")
    with pytest.raises(AuthenticationError):
        _authenticate(_authenticator(), token)


def test_unsupported_algorithm_is_rejected() -> None:
    token = mint_jwt(_SECRET, "analyst-1", algorithm="RS256")
    with pytest.raises(AuthenticationError):
        _authenticate(_authenticator(), token)


def test_missing_subject_is_rejected() -> None:
    token = mint_jwt(_SECRET, "", extra_claims={"sub": ""})
    with pytest.raises(AuthenticationError):
        _authenticate(_authenticator(), token)


def test_missing_expiry_is_rejected() -> None:
    token = mint_jwt(_SECRET, "analyst-1", extra_claims={"exp": None})
    with pytest.raises(AuthenticationError):
        _authenticate(_authenticator(), token)


def test_malformed_and_missing_credentials_are_rejected() -> None:
    auth = _authenticator()
    for bad in (None, "", "not-a-jwt", "a.b", "a.b.c.d"):
        with pytest.raises(AuthenticationError):
            _authenticate(auth, bad)


def test_missing_signing_secret_denies_everything() -> None:
    token = mint_jwt(_SECRET, "analyst-1")
    with pytest.raises(AuthenticationError):
        _authenticate(_authenticator(_EmptySecrets()), token)


# ---------------------------------------------------------- issuer / audience


def test_issuer_and_audience_are_enforced_when_configured() -> None:
    good = mint_jwt(
        _SECRET, "analyst-1", issuer="sentinel-idp", audience="sentinelai"
    )
    auth = _authenticator(issuer="sentinel-idp", audience="sentinelai")
    assert _authenticate(auth, good).subject == "analyst-1"

    wrong_issuer = mint_jwt(
        _SECRET, "analyst-1", issuer="evil", audience="sentinelai"
    )
    with pytest.raises(AuthenticationError):
        _authenticate(auth, wrong_issuer)

    wrong_audience = mint_jwt(
        _SECRET, "analyst-1", issuer="sentinel-idp", audience="other"
    )
    with pytest.raises(AuthenticationError):
        _authenticate(auth, wrong_audience)


def test_leeway_absorbs_small_clock_skew_on_expiry() -> None:
    # Token expired 10s ago; a 30s leeway still accepts it.
    token = mint_jwt(_SECRET, "analyst-1", expires_in=-10)
    assert _authenticate(_authenticator(leeway=30), token).subject == "analyst-1"
