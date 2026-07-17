"""Tests for Configuration (ES-029).

Covers the typed operational Environment and the startup Configuration Validation.
Each pure validation function is exercised in isolation with explicit settings
(no environment manipulation), so the tests are deterministic.
"""

import pytest
from pydantic import SecretStr, ValidationError

from app.config.ai import (
    ExternalKnowledgeProviderChoice,
    ExternalKnowledgeSettings,
)
from app.config.database import Neo4jSettings, PostgresSettings
from app.config.environment import Environment, resolve_environment
from app.config.errors import (
    InsecureSecretError,
    InvalidLogFormatError,
    UnknownEnvironmentError,
)
from app.config.log_format import LogFormat, resolve_log_format
from app.config.settings import Settings
from app.config.validation import (
    validate_configuration,
    validate_environment,
    validate_log_format,
    validate_secrets,
)

pytestmark = pytest.mark.operational

# ------------------------------------------------------------------- environment


def test_resolve_environment_maps_known_values() -> None:
    assert resolve_environment("development") is Environment.DEVELOPMENT
    assert resolve_environment("production") is Environment.PRODUCTION


def test_resolve_environment_is_case_and_whitespace_insensitive() -> None:
    assert resolve_environment("  Production ") is Environment.PRODUCTION


def test_resolve_environment_unknown_raises() -> None:
    with pytest.raises(UnknownEnvironmentError):
        resolve_environment("qa")


def test_is_production_like() -> None:
    assert Environment.DEVELOPMENT.is_production_like is False
    assert Environment.TEST.is_production_like is True
    assert Environment.STAGING.is_production_like is True
    assert Environment.PRODUCTION.is_production_like is True


def test_settings_environment_property() -> None:
    assert Settings(app_env="staging").environment is Environment.STAGING


def test_validate_environment_returns_typed_environment() -> None:
    assert validate_environment(Settings(app_env="test")) is Environment.TEST


def test_validate_environment_unknown_raises() -> None:
    with pytest.raises(UnknownEnvironmentError):
        validate_environment(Settings(app_env="qa"))


# ----------------------------------------------------------------------- secrets


def _postgres(password: str) -> PostgresSettings:
    return PostgresSettings(password=SecretStr(password))


def _neo4j(password: str) -> Neo4jSettings:
    return Neo4jSettings(password=SecretStr(password))


def test_development_is_lenient_with_insecure_defaults() -> None:
    # No exception: development may keep the placeholder secrets.
    validate_secrets(
        Environment.DEVELOPMENT, _postgres("change_me"), _neo4j("change_me")
    )


def test_production_rejects_insecure_postgres_secret() -> None:
    with pytest.raises(InsecureSecretError) as exc_info:
        validate_secrets(
            Environment.PRODUCTION, _postgres("change_me"), _neo4j("s3cret")
        )
    assert exc_info.value.setting_name == "POSTGRES_PASSWORD"


def test_production_rejects_insecure_neo4j_secret() -> None:
    with pytest.raises(InsecureSecretError) as exc_info:
        validate_secrets(
            Environment.PRODUCTION, _postgres("s3cret"), _neo4j("change_me")
        )
    assert exc_info.value.setting_name == "NEO4J_PASSWORD"


def test_production_passes_with_real_secrets() -> None:
    validate_secrets(Environment.PRODUCTION, _postgres("s3cret"), _neo4j("s3cret"))


def test_insecure_secret_error_never_leaks_the_value() -> None:
    error = InsecureSecretError("POSTGRES_PASSWORD")
    message = str(error)
    assert "POSTGRES_PASSWORD" in message
    assert "change_me" not in message


# --------------------------------------------------------------- orchestration


def test_validate_configuration_returns_resolved_environment() -> None:
    environment = validate_configuration(
        Settings(app_env="production"), _postgres("s3cret"), _neo4j("s3cret")
    )
    assert environment is Environment.PRODUCTION


def test_validate_configuration_fails_fast_on_insecure_secret() -> None:
    with pytest.raises(InsecureSecretError):
        validate_configuration(
            Settings(app_env="production"), _postgres("change_me"), _neo4j("s3cret")
        )


def test_error_codes_are_stable() -> None:
    assert UnknownEnvironmentError.code == "config.unknown_environment"
    assert InsecureSecretError.code == "config.insecure_secret"
    assert InvalidLogFormatError.code == "config.invalid_log_format"


# --------------------------------------------------------------------- log format


def test_resolve_log_format_maps_known_values() -> None:
    assert resolve_log_format("text") is LogFormat.TEXT
    assert resolve_log_format("  JSON ") is LogFormat.JSON


def test_resolve_log_format_unknown_raises() -> None:
    with pytest.raises(InvalidLogFormatError):
        resolve_log_format("xml")


def test_validate_log_format_returns_typed_value() -> None:
    assert validate_log_format(Settings(log_format="json")) is LogFormat.JSON


def test_validate_configuration_fails_fast_on_invalid_log_format() -> None:
    # Even in development (lenient on secrets), an invalid log format is rejected.
    with pytest.raises(InvalidLogFormatError):
        validate_configuration(
            Settings(app_env="development", log_format="xml"),
            _postgres("change_me"),
            _neo4j("change_me"),
        )


# ------------------------------------------------------- external knowledge


def test_external_knowledge_selection_parses_dedup_in_order() -> None:
    settings = ExternalKnowledgeSettings(providers=" nvd, attack , nvd ")

    assert settings.selection == (
        ExternalKnowledgeProviderChoice.NVD,
        ExternalKnowledgeProviderChoice.ATTACK,
    )


def test_external_knowledge_selection_is_case_insensitive() -> None:
    settings = ExternalKnowledgeSettings(providers="ATTACK")

    assert settings.selection == (ExternalKnowledgeProviderChoice.ATTACK,)


def test_external_knowledge_empty_value_opts_out() -> None:
    assert ExternalKnowledgeSettings(providers="").selection == ()


def test_external_knowledge_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ExternalKnowledgeSettings(providers="attack,virustotal")
