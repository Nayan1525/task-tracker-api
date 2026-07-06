"""Typed application settings.

Implements the single-typed-settings-object pattern from
`core/configuration-secrets.md` using pydantic-settings, and the cached
provider idiom from `frameworks/fastapi/idioms.md` so tests can override
config via FastAPI dependency overrides.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration, read once at startup and validated by pydantic.

    A missing/malformed required field raises here (fail fast) rather than
    deep inside a request. See `core/configuration-secrets.md`.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres via the psycopg (v3) driver. Overridden via DATABASE_URL in
    # every real environment; this default matches docker-compose.yml.
    database_url: str = (
        "postgresql+psycopg://task_tracker:task_tracker@localhost:5433/task_tracker"
    )
    environment: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Cached settings provider — injected via `Depends(get_settings)`."""
    return Settings()
