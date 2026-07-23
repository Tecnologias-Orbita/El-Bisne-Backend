from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "El Bisne API"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://el_bisne:el_bisne@localhost:5432/el_bisne"
    secret_key: str = "change-this-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    jwt_algorithm: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
