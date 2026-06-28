"""Redis async client lifecycle (connection primitive only).

Creates an async Redis client for the persistence foundation. This module
provides a connection primitive only: it defines no cache keys, semantics or
usage. Caching behaviour is owned by the services that require it.

The client is created lazily, so application startup and unit tests do not
require a live Redis instance.
"""

from redis.asyncio import Redis, from_url

from app.config.database import RedisSettings


def create_client(settings: RedisSettings) -> Redis:
    """Create the async Redis client for the given settings."""

    return from_url(settings.url)
