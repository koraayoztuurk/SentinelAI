"""Configuration validation.

Implements the Configuration Validation lifecycle stage (configuration-management
§8): a fail-fast check that the loaded configuration is consistent with the active
environment before the application serves traffic. It is invoked from the startup
lifespan.

``validate_configuration`` only orchestrates; each concrete rule is a small pure
function so rules can be tested in isolation and new rules added without touching
the others. The functions are pure over their arguments (they read no environment
themselves), which keeps them deterministic and independently testable.

ES-069 adds **secret availability** (secrets-management §6): outside development,
a deployment that cannot perform the capabilities it is configured for must not
enter service claiming it can. This is the one rule that needs more than
settings — resolving a secret needs the store — so the provider is injected by
the composition root and the rule stays optional here.

The set of insecure default values stays internal to this module — errors report
only the offending setting's name, never a secret or placeholder value.
"""

from pydantic import SecretStr

from app.application.secrets import (
    SecretName,
    SecretNotFoundError,
    SecretProvider,
)
from app.config.ai import LLMProviderChoice, LLMSelectionSettings
from app.config.auth import AuthProviderChoice, AuthSelectionSettings
from app.config.database import Neo4jSettings, PostgresSettings
from app.config.environment import Environment, resolve_environment
from app.config.errors import InsecureSecretError, MissingSecretError
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


def required_secret_names(
    settings: Settings,
    auth: AuthSelectionSettings,
    llm: LLMSelectionSettings,
) -> tuple[SecretName, ...]:
    """Return the secrets the *configured* capabilities require (ES-069).

    Derived from configuration rather than fixed, because what a deployment
    needs is what it says it will do: the JWT verifier needs its signing
    secret only when it is the selected authenticator, the NVIDIA key only
    when NVIDIA is selected as the primary or the fallback provider, and the
    embedding key only while the projector that derives embeddings is running.

    ``NVD_API_KEY`` is deliberately absent: NVD's own contract makes it
    optional (keyless access is merely rate-limited harder), so requiring it
    would refuse startup over a capability that works without it.
    """

    required: list[SecretName] = []

    if auth.provider is AuthProviderChoice.JWT:
        required.append(SecretName("AUTH_JWT_SECRET"))
    else:
        required.append(SecretName("DEV_AUTH_TOKEN"))

    providers = {llm.provider}
    if llm.fallback_provider is not None:
        providers.add(llm.fallback_provider)
    if LLMProviderChoice.GEMINI in providers:
        required.append(SecretName("GOOGLE_API_KEY"))
    if LLMProviderChoice.NVIDIA in providers:
        required.append(SecretName("NVIDIA_API_KEY"))

    # Embedding stays on the Gemini adapter regardless of the LLM selection
    # (the vector dimension is bound to it, ES-050), so the projector needs
    # the Google key even in an NVIDIA-only deployment.
    if settings.outbox_projector_enabled:
        google = SecretName("GOOGLE_API_KEY")
        if google not in required:
            required.append(google)

    return tuple(required)


def validate_secret_availability(
    environment: Environment,
    provider: SecretProvider,
    required: tuple[SecretName, ...],
) -> None:
    """Reject startup when a configured capability has no secret (ES-069).

    Development keeps lazy per-request resolution so a partially configured
    environment stays workable (secrets-management §6); every other
    environment must be able to do what it claims before it serves traffic.

    Every missing secret is reported at once — an operator fixing a
    misconfiguration should not have to discover it one restart at a time.
    """

    if not environment.is_production_like:
        return

    missing = tuple(
        name.value for name in required if not _is_available(provider, name)
    )
    if missing:
        raise MissingSecretError(missing)


def _is_available(provider: SecretProvider, name: SecretName) -> bool:
    try:
        return bool(provider.resolve(name).reveal().strip())
    except SecretNotFoundError:
        return False


def validate_configuration(
    settings: Settings,
    postgres: PostgresSettings,
    neo4j: Neo4jSettings,
    *,
    auth: AuthSelectionSettings | None = None,
    llm: LLMSelectionSettings | None = None,
    secrets: SecretProvider | None = None,
) -> Environment:
    """Validate the configuration and return the resolved environment.

    Raises a :class:`~app.config.errors.ConfigurationError` subtype on the first
    violation (fail-fast).

    The secret-availability check runs only when a provider is supplied: the
    settings-based rules are pure over their arguments, while resolving a
    secret needs the store, which the composition root owns.
    """

    environment = validate_environment(settings)
    validate_log_format(settings)
    validate_secrets(environment, postgres, neo4j)
    if secrets is not None and auth is not None and llm is not None:
        validate_secret_availability(
            environment, secrets, required_secret_names(settings, auth, llm)
        )
    return environment


def _reject_insecure_default(setting_name: str, secret: SecretStr) -> None:
    if secret.get_secret_value() in _INSECURE_SECRET_DEFAULTS:
        raise InsecureSecretError(setting_name)
