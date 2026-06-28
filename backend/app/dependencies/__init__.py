"""Dependency-injection providers.

This package holds **only** FastAPI dependency providers — callables intended for
use with :func:`fastapi.Depends`. It contains no business logic, services or
configuration definitions of its own; it merely exposes existing capabilities as
injectable dependencies.

It establishes the dependency-injection pattern for the backend: future
providers (for example, ``Depends``-injected services and repositories) are added
here as later specifications introduce them.
"""

from app.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
