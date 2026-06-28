"""SentinelAI backend application package.

This package contains the backend architectural skeleton for SentinelAI.
It establishes the architectural layers, application lifecycle, configuration,
logging and shared infrastructure on which future engineering specifications
build business capabilities.

The package version is resolved from the installed distribution metadata so that
``pyproject.toml`` remains the single source of truth for the version number.
"""

from importlib import metadata

try:
    __version__ = metadata.version("sentinelai-backend")
except metadata.PackageNotFoundError:  # pragma: no cover - running from source tree
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
