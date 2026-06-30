"""Secrets infrastructure.

Concrete :class:`~app.application.secrets.SecretProvider` adapters. The default
``EnvironmentSecretProvider`` resolves secrets from the environment; a durable
vault adapter is introduced by a later specification.
"""

from app.infrastructure.secrets.environment import EnvironmentSecretProvider

__all__ = ["EnvironmentSecretProvider"]
