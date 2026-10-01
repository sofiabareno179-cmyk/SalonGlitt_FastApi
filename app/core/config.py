"""Application settings loaded from environment variables.

Secrets never live in this file: they are read from the process
environment or from a local .env that is git-ignored.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration. A missing required value aborts startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SGE_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SGE-API"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # No defaults on purpose: startup must fail loudly when a secret
    # is missing. Both values come from SGE_SECRET_KEY and
    # SGE_DATABASE_URL in the git-ignored .env file.
    secret_key: str
    database_url: str

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)

    # Origins allowed to call this API from a browser.
    # Native Flutter (Android/iOS) does NOT send Origin, so it is unaffected.
    cors_origins: list[str] = [
        "http://localhost:8030",      # React admin panel
        "http://127.0.0.1:8030",
        "http://localhost:3000",      # flutter run -d chrome
    ]


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the .env file is parsed only once."""
    return Settings()