"""Production JWT bearer authenticator (ES-062).

The production-grade realization of the presentation ``Authenticator`` port
(authentication-authorization §4/§5), replacing the dev-grade shared token at
runtime selection (``AUTH_PROVIDER=jwt``). It **verifies** a signed bearer JWT
— the platform is a verifier, not an issuer: token issuance belongs to the
external identity provider (§4 External Identities); a dev minting utility
(``scripts/mint_dev_jwt.py``) stands in for that issuer in local/test use.

Verification is HS256 over the standard library only (no vendor SDK — the
NVIDIA/Gemini adapter discipline): the signature is recomputed with the shared
secret and compared in constant time, and the algorithm is **fixed** to HS256.
Fixing the algorithm closes the ``alg:none`` and RS/HS confusion downgrade
attacks — a token whose header names any other algorithm is rejected outright.

Claims: ``sub`` establishes the traceable subject (§4 "uniquely identifiable /
traceable"); ``exp`` is required and enforced with a small leeway (§5
"Authentication Continuity" — identity is valid only until its context
expires); ``nbf`` (optional) must not be in the future; ``iss``/``aud``
(optional) must match when configured. The ``kind`` claim distinguishes
human/system/external identities (defaulting to human). The signing secret is a
protected asset consumed through the ``SecretProvider`` (``AUTH_JWT_SECRET``);
a missing secret denies every request (secure by default), and no credential
material ever appears in errors or logs.
"""

import base64
import hashlib
import hmac
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import Request

from app.application.secrets import (
    SecretName,
    SecretNotFoundError,
    SecretProvider,
)
from app.config.auth import JwtSettings
from app.presentation.api.auth import AuthenticatedIdentity, IdentityKind
from app.presentation.api.errors import AuthenticationError

logger = logging.getLogger(__name__)

AUTH_JWT_SECRET = SecretName("AUTH_JWT_SECRET")

# The only accepted signature algorithm (see module docstring — a fixed
# algorithm closes the alg:none / algorithm-confusion downgrade surface).
_ALGORITHM = "HS256"


def _b64url_decode(segment: str) -> bytes:
    """Decode a base64url JWT segment, restoring stripped padding."""

    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


class JwtAuthenticator:
    """``Authenticator`` adapter verifying HS256-signed bearer JWTs."""

    def __init__(
        self,
        settings: JwtSettings,
        secrets: SecretProvider,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._settings = settings
        self._secrets = secrets
        # Injectable clock keeps the exp/nbf tests deterministic; presentation
        # may hold a clock (the domain/services no-clock rule does not apply).
        self._now = now or (lambda: datetime.now(UTC))

    async def authenticate(self, request: Request) -> AuthenticatedIdentity:
        token = self._bearer_token(request)
        secret = self._resolve_secret()
        claims = self._verify(token, secret)
        return self._identity(claims)

    @staticmethod
    def _bearer_token(request: Request) -> str:
        header = request.headers.get("Authorization", "")
        scheme, _, credential = header.partition(" ")
        if scheme.lower() != "bearer" or not credential.strip():
            raise AuthenticationError("Missing or malformed bearer credential.")
        return credential.strip()

    def _resolve_secret(self) -> str:
        try:
            return self._secrets.resolve(AUTH_JWT_SECRET).reveal().strip()
        except SecretNotFoundError as exc:
            # Secure by default: without a verification secret every request
            # is rejected, identical to the unconfigured seam.
            raise AuthenticationError(
                "No authentication provider is configured."
            ) from exc

    def _verify(self, token: str, secret: str) -> dict[str, object]:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Malformed bearer credential.")
        header_segment, payload_segment, signature_segment = parts

        self._verify_algorithm(header_segment)
        self._verify_signature(
            header_segment, payload_segment, signature_segment, secret
        )
        claims = self._decode_claims(payload_segment)
        self._verify_time(claims)
        self._verify_issuer_audience(claims)
        return claims

    @staticmethod
    def _verify_algorithm(header_segment: str) -> None:
        try:
            header = json.loads(_b64url_decode(header_segment))
        except (ValueError, TypeError) as exc:
            raise AuthenticationError("Malformed bearer credential.") from exc
        if not isinstance(header, dict) or header.get("alg") != _ALGORITHM:
            # Any algorithm other than the fixed one (including "none") is
            # rejected before the signature is even considered.
            raise AuthenticationError("Unsupported token algorithm.")

    @staticmethod
    def _verify_signature(
        header_segment: str,
        payload_segment: str,
        signature_segment: str,
        secret: str,
    ) -> None:
        signing_input = f"{header_segment}.{payload_segment}".encode()
        expected = hmac.new(
            secret.encode(), signing_input, hashlib.sha256
        ).digest()
        try:
            provided = _b64url_decode(signature_segment)
        except (ValueError, TypeError) as exc:
            raise AuthenticationError("Invalid credential.") from exc
        if not hmac.compare_digest(expected, provided):
            raise AuthenticationError("Invalid credential.")

    @staticmethod
    def _decode_claims(payload_segment: str) -> dict[str, object]:
        try:
            claims = json.loads(_b64url_decode(payload_segment))
        except (ValueError, TypeError) as exc:
            raise AuthenticationError("Malformed bearer credential.") from exc
        if not isinstance(claims, dict):
            raise AuthenticationError("Malformed bearer credential.")
        return claims

    def _verify_time(self, claims: dict[str, object]) -> None:
        now = self._now().timestamp()
        leeway = self._settings.leeway_seconds

        expiry = claims.get("exp")
        if not isinstance(expiry, (int, float)) or isinstance(expiry, bool):
            # exp is required: an identity must carry a validity horizon.
            raise AuthenticationError("Token has no expiry.")
        if now > float(expiry) + leeway:
            raise AuthenticationError("Token has expired.")

        not_before = claims.get("nbf")
        if isinstance(not_before, (int, float)) and not isinstance(
            not_before, bool
        ):
            if now < float(not_before) - leeway:
                raise AuthenticationError("Token is not yet valid.")

    def _verify_issuer_audience(self, claims: dict[str, object]) -> None:
        if self._settings.issuer and claims.get("iss") != self._settings.issuer:
            raise AuthenticationError("Token issuer is not accepted.")
        if self._settings.audience:
            audience = claims.get("aud")
            accepted = (
                self._settings.audience in audience
                if isinstance(audience, list)
                else audience == self._settings.audience
            )
            if not accepted:
                raise AuthenticationError("Token audience is not accepted.")

    @staticmethod
    def _identity(claims: dict[str, object]) -> AuthenticatedIdentity:
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise AuthenticationError("Token has no subject.")
        kind_token = claims.get("kind", IdentityKind.HUMAN.value)
        try:
            kind = IdentityKind(kind_token)
        except ValueError as exc:
            raise AuthenticationError("Token has an unknown identity kind.") from exc
        logger.info("jwt verified subject=%s kind=%s", subject.strip(), kind.value)
        return AuthenticatedIdentity(subject=subject.strip(), kind=kind)
