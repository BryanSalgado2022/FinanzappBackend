from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    google_client_id: str
    # Optional (unlike google_client_id/jwt_secret): the AI chat agent is a
    # standalone feature, not core auth - the rest of the app must keep
    # working when this isn't configured yet.
    gemini_api_key: str | None = None
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173"
    dev_mode: bool = False

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        # Railway's auto-injected DATABASE_URL (and Heroku-style URLs
        # generally) omit the driver - SQLAlchemy then defaults to psycopg2,
        # which isn't installed here (this project uses psycopg v3). Force
        # the psycopg v3 dialect unless a driver is already specified.
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://") :]
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
