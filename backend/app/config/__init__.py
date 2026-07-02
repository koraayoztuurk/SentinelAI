"""Configuration management.

Owns the application configuration loaded from the environment. Configuration
adapts operational behaviour without redefining architectural responsibilities,
consistent with the Configuration Management architecture document.

Configuration model (configuration-management §5/§6) — every item has a single owner:

- **Platform Configuration** → ``settings.py`` (application identity, host/port, log
  level): platform-wide operational behaviour.
- **Domain Configuration** → ``database.py`` (per-store Postgres/Neo4j/Qdrant/Redis
  groups): owned by the persistence domain that consumes it.
- **Environment Configuration** → ``environment.py`` (the typed :class:`Environment`)
  and ``validation.py`` (the startup Configuration Validation, §8): adapts and guards
  operational behaviour per environment without introducing architectural differences.
- **Deployment Configuration** → the container/compose build args (ES-028) for the
  backend and the frontend's ``communication/config.ts``: owned by each deployment unit.

Secret *values* are owned by the Secrets Management foundation (ES-022); configuration
here references secrets but never logs or exposes their values.
"""

from app.config.environment import Environment, resolve_environment
from app.config.errors import (
    ConfigurationError,
    InsecureSecretError,
    UnknownEnvironmentError,
)
from app.config.settings import Settings, get_settings
from app.config.validation import validate_configuration

__all__ = [
    "Settings",
    "get_settings",
    "Environment",
    "resolve_environment",
    "validate_configuration",
    "ConfigurationError",
    "UnknownEnvironmentError",
    "InsecureSecretError",
]
