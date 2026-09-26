from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://drilllens:drilllens@localhost:5432/drilllens"
    secret_key: str = "change-me-secret-key"
    jwt_secret_key: str = "change-me-jwt-secret"
    jwt_access_token_expire_minutes: int = 60
    jwt_remember_minutes: int = 10080
    upload_directory: str = "uploads"
    max_upload_size_mb: int = 25
    tesseract_path: str = ""
    ocr_language: str = "eng"
    cors_origins: str = "http://localhost:8080,http://localhost:5173"
    websocket_interval_seconds: float = 2.0
    osm_tile_url: str = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    environment: str = "development"
    return_reset_token: bool = True
    sensor_adapter: str = "simulated"
    risk_engine: str = "rule_based"
    enable_spacy: bool = True
    enable_transformers: bool = False
    app_version: str = "1.0.0"
    app_name: str = "DrillLens"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"development", "dev", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
