"""Response cache policy (ES-068).

Realizes the §13 Response Caching posture. The enumeration of what the backend
serves ends with nothing cacheable, and that is a conclusion rather than an
omission:

- every ``/api`` response is scoped to the requesting identity and its tenant
  (ADR-016), so a shared cached copy could be served across an ownership
  boundary;
- investigation-scoped data has an end of life — erasure may redact a resource
  at any moment (ADR-017, data-lifecycle §3) — so a stored copy could outlive
  its own erasure, which is a compliance failure, not a stale read;
- the operational endpoints answer "is this instance healthy *now*"; a cached
  health answer is indistinguishable from a stale one.

So the backend declares its responses non-storable and the platform's cacheable
surface is the immutable, content-hashed presentation assets, cached at the
deployment edge where they belong. Admitting a cacheable API surface later means
showing that neither the ownership nor the erasure rule applies to it — a
per-surface decision made in code with the response it governs, not an
environment variable that could silently turn an erased resource back on.

Implemented as a plain ASGI middleware rather than a ``BaseHTTPMiddleware``:
setting one header needs no request/response objects and no per-request task
group, and this way the policy also covers error responses and streaming
payload downloads uniformly.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CACHE_CONTROL_HEADER = "cache-control"
NO_STORE = "no-store"

_API_PREFIX = "/api/"
_OPERATIONAL_PATHS = frozenset({"/health", "/health/ready", "/metrics"})


def is_non_storable(path: str) -> bool:
    """Whether responses for ``path`` must never be stored by any cache."""

    return path.startswith(_API_PREFIX) or path in _OPERATIONAL_PATHS


class CacheControlMiddleware:
    """Applies the platform's cache policy to every response it governs."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http" or not is_non_storable(scope["path"]):
            await self.app(scope, receive, send)
            return

        async def send_with_policy(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                # An endpoint that has already declared its own policy keeps
                # it; the middleware supplies the platform default.
                if CACHE_CONTROL_HEADER not in headers:
                    headers[CACHE_CONTROL_HEADER] = NO_STORE
            await send(message)

        await self.app(scope, receive, send_with_policy)
