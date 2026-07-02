"""Configuration validation.

Implements the Configuration Validation lifecycle stage (configuration-management
§8): a fail-fast check that the loaded configuration is consistent with the active
environment before the application serves traffic. It is invoked from the startup
lifespan.

``validate_configuration`` only orchestrates; each concrete rule is a small pure
function so rules can be tested in isolation and new rules added without touching
the others. The functions are pure over their arguments (they read no environment
themselves), which keeps them deterministic and independently testable.

The set of insecure default values stays internal to this module — errors report
only the offending setting's name, never a secret or placeholder value.
"""

from pydantic import SecretStr

from app.config.database import Neo4jSettings, PostgresSettings
from app.config.environment import Environment, resolve_environment
from app.config.errors import InsecureSecretError
from app.config.log_format import LogFormat, resolve_log_format
from app.config.settings import Settings

# Known insecure placeholder secrets that must not reach a production-like
# environment. Kept private so it is never surfaced in an error message or log.
_INSECURE_SECRET_DEFAULTS: frozenset[str] = frozenset({"change_me"})


def validate_environment(settings: Settings) -> Environment:
    """Resolve and validate the active operational environment."""

    return resolve_environment(settings.app_env)


def validate_log_format(settings: Settings) -> LogFormat:
    """Resolve and validate the configured log output format."""

    return resolve_log_format(settings.log_format)


def validate_secrets(
    environment: Environment,
    postgres: PostgresSettings,
    neo4j: Neo4jSettings,
) -> None:
    """Reject secret-bearing settings left at an insecure default.

    Development is intentionally lenient (the placeholders are a local
    convenience); every production-like environment must supply real secrets.
    """

    if not environment.is_production_like:
        return

    _reject_insecure_default("POSTGRES_PASSWORD", postgres.password)
    _reject_insecure_default("NEO4J_PASSWORD", neo4j.password)


def validate_configuration(
    settings: Settings,
    postgres: PostgresSettings,
    neo4j: Neo4jSettings,
) -> Environment:
    """Validate the configuration and return the resolved environment.

    Raises a :class:`~app.config.errors.ConfigurationError` subtype on the first
    violation (fail-fast).
    """

    environment = validate_environment(settings)
    validate_log_format(settings)
    validate_secrets(environment, postgres, neo4j)
    return environment


def _reject_insecure_default(setting_name: str, secret: SecretStr) -> None:
    if secret.get_secret_value() in _INSECURE_SECRET_DEFAULTS:
        raise InsecureSecretError(setting_name)
