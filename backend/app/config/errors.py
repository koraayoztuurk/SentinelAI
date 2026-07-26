"""Configuration exceptions.

Startup/configuration failures. They derive from the shared
:class:`~app.shared.exceptions.SentinelAIError` and carry stable, machine-readable
``code`` values. Configuration errors never include a secret value or a placeholder
value in their message — :class:`InsecureSecretError` reports only the name of the
offending setting, so the error model stays stable even as validation rules grow.
"""

from app.shared.exceptions import SentinelAIError


class ConfigurationError(SentinelAIError):
    """Base class for configuration validation failures."""

    code = "config.invalid"


class UnknownEnvironmentError(ConfigurationError):
    """Raised when ``app_env`` is not one of the recognized environments."""

    code = "config.unknown_environment"


class InvalidLogFormatError(ConfigurationError):
    """Raised when ``log_format`` is not one of the recognized log formats."""

    code = "config.invalid_log_format"


class InsecureSecretError(ConfigurationError):
    """Raised when a secret-bearing setting is left at an insecure default.

    The offending setting's name is preserved (never its value) so operators can
    identify what to fix without the error leaking or naming the placeholder value.
    """

    code = "config.insecure_secret"

    def __init__(self, setting_name: str) -> None:
        self.setting_name = setting_name
        super().__init__(
            f"Configuration '{setting_name}' must be set to a non-default value "
            f"outside development environments."
        )


class MissingSecretError(ConfigurationError):
    """Raised when a capability the deployment declares has no secret (ES-069).

    An absent secret is a **configuration** failure, not a runtime one
    (secrets-management §6): outside development a deployment that cannot
    perform the capabilities it is configured for does not enter service. The
    error names the missing secrets' identities, never any value.
    """

    code = "config.missing_secret"

    def __init__(self, secret_names: tuple[str, ...]) -> None:
        self.secret_names = secret_names
        listed = ", ".join(secret_names)
        super().__init__(
            f"Required secrets are not available: {listed}. The configured "
            f"capabilities cannot be provided outside development environments."
        )
