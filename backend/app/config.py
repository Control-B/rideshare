from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mobility Platform API"
    environment: str = "development"
    database_url: str = "sqlite:///./mobility.db"
    jwt_secret: str = "local-demo-secret-change-me-at-least-32-bytes"
    access_token_minutes: int = 720
    cors_origins: str = "http://localhost:8081,http://localhost:19006"
    dispatch_search_radii_miles: str = "2,5,10"
    driver_location_stale_seconds: int = 90
    driver_presence_ttl_seconds: int = 120
    driver_max_accuracy_meters: float = 100
    driver_max_speed_mps: float = 70
    dispatch_offer_seconds: int = 45
    dispatch_offer_group_size: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MOBILITY_", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def dispatch_radii(self) -> list[float]:
        values = [float(value.strip()) for value in self.dispatch_search_radii_miles.split(",")]
        if not values or any(value <= 0 for value in values):
            raise ValueError("Dispatch search radii must be positive")
        return sorted(set(values))


@lru_cache
def get_settings() -> Settings:
    return Settings()
