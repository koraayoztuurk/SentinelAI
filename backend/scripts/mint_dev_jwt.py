"""Dev JWT issuance utility (ES-062).

Stands in for the external identity provider so a developer can mint a bearer
token the production ``JwtAuthenticator`` (``AUTH_PROVIDER=jwt``) accepts. The
running platform is a verifier, not an issuer (authentication-authorization §4)
— this issuance lives only here, never in ``app``.

Usage (from ``backend/``):

    python scripts/mint_dev_jwt.py --subject koray --kind human --ttl 3600

The signing secret is read from ``AUTH_JWT_SECRET`` in the environment (the same
secret the verifier resolves through the SecretProvider). Print the token and
send it as ``Authorization: Bearer <token>``.
"""

import argparse
import os
import sys

# The minting helper lives in test support (issuance is not app code).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.support.jwt import mint_jwt  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Mint a dev JWT for SentinelAI.")
    parser.add_argument("--subject", required=True, help="the token subject (sub)")
    parser.add_argument(
        "--kind",
        default="human",
        choices=("human", "system", "external"),
        help="identity kind claim",
    )
    parser.add_argument(
        "--ttl", type=int, default=3600, help="seconds until expiry"
    )
    parser.add_argument("--issuer", default=None, help="optional iss claim")
    parser.add_argument("--audience", default=None, help="optional aud claim")
    args = parser.parse_args()

    secret = os.environ.get("AUTH_JWT_SECRET", "").strip()
    if not secret:
        print(
            "AUTH_JWT_SECRET is not set — export it (the verifier's secret).",
            file=sys.stderr,
        )
        return 1

    token = mint_jwt(
        secret,
        args.subject,
        kind=args.kind,
        expires_in=args.ttl,
        issuer=args.issuer,
        audience=args.audience,
    )
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
