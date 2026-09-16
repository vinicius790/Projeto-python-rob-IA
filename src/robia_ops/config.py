from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_PII_KEY = "robia-dev-pii-key-change-me"


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or ``.env``.

    Production deliberately has stricter validation than local development.  This
    keeps the demo convenient without letting an obviously unsafe configuration be
    promoted accidentally.
    """

    model_config = SettingsConfigDict(
        env_prefix="ROBIA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "RobIA Ops"
    app_version: str = "3.0.0"
    env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: str = "sqlite:///./data/robia.db"

    # Legacy single key remains supported.  Scoped keys are preferred.
    api_key: SecretStr | None = None
    read_api_key: SecretStr | None = None
    write_api_key: SecretStr | None = None
    admin_api_key: SecretStr | None = None
    pii_key: SecretStr = SecretStr(_DEV_PII_KEY)

    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    allowed_origins: str = ""
    log_level: str = "INFO"
    provider: Literal["sandbox"] = "sandbox"
    enable_docs: bool = True
    enable_dashboard: bool = True
    enable_metrics: bool = True
    max_page_size: int = 100
    max_request_bytes: int = 1_048_576
    anomaly_contamination: float = 0.08
    provider_max_attempts: int = 3
    provider_retry_base_seconds: float = 0.05
    default_currency: str = "BRL"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 1800
    sqlite_busy_timeout_ms: int = 5000

    @field_validator("max_page_size")
    @classmethod
    def validate_page_size(cls, value: int) -> int:
        if not 1 <= value <= 500:
            raise ValueError("max_page_size must be between 1 and 500")
        return value

    @field_validator("max_request_bytes")
    @classmethod
    def validate_request_size(cls, value: int) -> int:
        if not 1_024 <= value <= 20 * 1024 * 1024:
            raise ValueError("max_request_bytes must be between 1 KiB and 20 MiB")
        return value

    @field_validator("anomaly_contamination")
    @classmethod
    def validate_contamination(cls, value: float) -> float:
        if not 0.001 <= value <= 0.5:
            raise ValueError("anomaly_contamination must be between 0.001 and 0.5")
        return value

    @field_validator("provider_max_attempts")
    @classmethod
    def validate_attempts(cls, value: int) -> int:
        if not 1 <= value <= 10:
            raise ValueError("provider_max_attempts must be between 1 and 10")
        return value

    @field_validator("provider_retry_base_seconds")
    @classmethod
    def validate_retry_delay(cls, value: float) -> float:
        if not 0 <= value <= 10:
            raise ValueError("provider_retry_base_seconds must be between 0 and 10")
        return value

    @field_validator("db_pool_size", "db_max_overflow")
    @classmethod
    def validate_pool_values(cls, value: int) -> int:
        if not 0 <= value <= 100:
            raise ValueError("database pool values must be between 0 and 100")
        return value

    @field_validator("db_pool_recycle_seconds", "sqlite_busy_timeout_ms")
    @classmethod
    def validate_timeouts(cls, value: int) -> int:
        if not 0 <= value <= 86_400_000:
            raise ValueError("database timeout value is outside the accepted range")
        return value

    @field_validator("default_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("default_currency must be a three-letter ISO-style code")
        return value

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.env == "production":
            if not (self.admin_api_key or self.api_key):
                raise ValueError("ROBIA_ADMIN_API_KEY or ROBIA_API_KEY is required in production")
            if self.pii_key.get_secret_value() == _DEV_PII_KEY:
                raise ValueError("ROBIA_PII_KEY must be changed in production")
            if self.debug:
                raise ValueError("ROBIA_DEBUG must be false in production")
        return self

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_hosts.split(",") if item.strip()]

    @property
    def allowed_origins_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def dashboard_enabled(self) -> bool:
        # The bundled dashboard is intentionally read-only and development focused.
        return self.enable_dashboard and not self.is_production

    @property
    def docs_enabled(self) -> bool:
        return self.enable_docs and not self.is_production

    @property
    def auth_enabled(self) -> bool:
        return any((self.api_key, self.read_api_key, self.write_api_key, self.admin_api_key))

    def ensure_runtime_dirs(self) -> None:
        if self.database_url.startswith("sqlite:///"):
            raw = self.database_url.removeprefix("sqlite:///")
            if raw != ":memory:":
                Path(raw).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
