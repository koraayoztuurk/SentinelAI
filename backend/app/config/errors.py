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
