from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mobility Platform API"
    environment: str = "development"
    database_url: str = "sqlite:///./mobility.db"
    jwt_secret: str = "local-demo-secret-change-me-at-least-32-bytes"
    access_token_minutes: int = 720
    cors_origins: str = "http://localhost:8081,http://localhost:19006"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MOBILITY_", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
