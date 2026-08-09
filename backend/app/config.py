"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    database_url: str = "sqlite:///./personal_planner.db"
    api_prefix: str = "/api/v1"
    frontend_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_prefix="PLANNER_",
        env_file=".env",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
