"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    require_auth: bool = False
    access_username: str | None = None
    access_password: SecretStr | None = None
    frontend_dist: Path | None = None

    model_config = SettingsConfigDict(
        env_prefix="PLANNER_",
        env_file=".env",
    )

    @model_validator(mode="after")
    def validate_deployment(self) -> Self:
        """Reject incomplete production and access-control configuration."""
        if self.require_auth and (
            not self.access_username
            or self.access_password is None
            or not self.access_password.get_secret_value()
        ):
            msg = "Access username and password are required when authentication is enabled."
            raise ValueError(msg)
        if self.environment == "production":
            if not self.require_auth:
                msg = "Production requires authentication."
                raise ValueError(msg)
            if self.frontend_dist is None or not (self.frontend_dist / "index.html").is_file():
                msg = "Production requires a frontend build containing index.html."
                raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
