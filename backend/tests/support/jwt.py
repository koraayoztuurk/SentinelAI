"""HS256 JWT minting for tests and the dev issuance utility (ES-062).

The platform is a token *verifier*, not an issuer (authentication-authorization
§4): issuance belongs to the external identity provider. This helper stands in
for that issuer so tests and the local demo can mint tokens the
``JwtAuthenticator`` accepts. It deliberately lives in test support / the dev
script, never in ``app`` — the running platform grows no issuance surface.
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def mint_jwt(
    secret: str,
    subject: str,
    *,
    kind: str = "human",
    expires_in: int = 3600,
    not_before: int | None = None,
    issuer: str | None = None,
    audience: str | None = None,
    algorithm: str = "HS256",
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Mint an HS256 JWT for ``subject`` valid for ``expires_in`` seconds.

    ``algorithm`` is overridable so adversarial tests can forge an ``alg:none``
    or wrong-algorithm header; the verifier must reject anything but HS256.
    """

    now = int(time.time())
    header = {"alg": algorithm, "typ": "JWT"}
    claims: dict[str, Any] = {
        "sub": subject,
        "kind": kind,
        "iat": now,
        "exp": now + expires_in,
    }
    if not_before is not None:
        claims["nbf"] = not_before
    if issuer is not None:
        claims["iss"] = issuer
    if audience is not None:
        claims["aud"] = audience
    if extra_claims:
        claims.update(extra_claims)

    header_segment = _b64url(json.dumps(header).encode())
    payload_segment = _b64url(json.dumps(claims).encode())
    signing_input = f"{header_segment}.{payload_segment}".encode()
    if algorithm == "none":
        signature = ""
    else:
        signature = _b64url(
            hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        )
    return f"{header_segment}.{payload_segment}.{signature}"
