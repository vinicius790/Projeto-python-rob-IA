import pytest
from pydantic import ValidationError

from robia_ops.config import Settings


def test_allowed_hosts_and_origins_are_split() -> None:
    settings = Settings(
        _env_file=None,
        allowed_hosts="localhost, example.test",
        allowed_origins="https://one.test, https://two.test",
    )
    assert settings.allowed_hosts_list == ["localhost", "example.test"]
    assert settings.allowed_origins_list == ["https://one.test", "https://two.test"]


def test_guardrails() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_page_size=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, anomaly_contamination=0.9)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_request_bytes=100)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, provider_max_attempts=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, default_currency="real")


def test_production_requires_auth_and_custom_pii_key() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, env="production")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, env="production", api_key="prod-secret")


def test_production_security_posture() -> None:
    settings = Settings(
        _env_file=None,
        env="production",
        admin_api_key="prod-admin",
        pii_key="production-pii-key",
    )
    assert settings.auth_enabled is True
    assert settings.dashboard_enabled is False
    assert settings.docs_enabled is False
    assert "prod-admin" not in repr(settings)
    assert "production-pii-key" not in repr(settings)
