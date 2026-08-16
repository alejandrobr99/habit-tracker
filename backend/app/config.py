"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_REQUEST_BYTES = 1024
MAX_REQUEST_BYTES = 1_048_576
MAX_TRUSTED_PROXY_HOPS = 4
OCR_BUDGET_MICROUSD = 10_000_000


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    environment: Literal["development", "production"] = "development"
    database_url: str = "sqlite:///./personal_planner.db"
    api_prefix: str = "/api/v1"
    frontend_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    allowed_hosts: list[str] = [
        "localhost",
        "127.0.0.1",
        "testserver",
    ]
    bootstrap_admin_username: str | None = None
    bootstrap_admin_display_name: str = "Administrador"
    bootstrap_admin_password: SecretStr | None = None
    frontend_dist: Path | None = None
    trusted_proxy_hops: int = Field(default=0, ge=0, le=MAX_TRUSTED_PROXY_HOPS)
    max_request_bytes: int = Field(
        default=65_536,
        ge=MIN_REQUEST_BYTES,
        le=MAX_REQUEST_BYTES,
    )
    gemini_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "PLANNER_GEMINI_API_KEY"),
    )
    ocr_enabled: bool = False
    ocr_budget_microusd: int = Field(default=OCR_BUDGET_MICROUSD, ge=0)
    ocr_max_request_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=MIN_REQUEST_BYTES,
        le=50 * 1024 * 1024,
    )
    ocr_max_calls_per_hour: int = Field(default=20, ge=1, le=100)

    model_config = SettingsConfigDict(
        env_prefix="PLANNER_",
        env_file=".env",
    )

    @model_validator(mode="after")
    def validate_deployment(self) -> Self:
        """Reject incomplete production and access-control configuration."""
        has_bootstrap_username = bool(self.bootstrap_admin_username)
        has_bootstrap_password = bool(
            self.bootstrap_admin_password and self.bootstrap_admin_password.get_secret_value(),
        )
        if has_bootstrap_username != has_bootstrap_password:
            msg = "Bootstrap username and password must be configured together."
            raise ValueError(msg)
        if self.environment == "production" and (
            self.frontend_dist is None or not (self.frontend_dist / "index.html").is_file()
        ):
            msg = "Production requires a frontend build containing index.html."
            raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
