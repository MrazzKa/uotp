from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+asyncpg://uotp:uotp@localhost:5432/uotp"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_public_endpoint: str = "http://localhost:9000"
    minio_root_user: str = "uotp_minio"
    minio_root_password: str = "uotp_minio_password"
    minio_bucket: str = "uotp-files"
    jwt_secret: str = Field(default="change-me-in-real-env-with-at-least-32-bytes")
    jwt_algorithm: str = "HS256"
    access_token_ttl: int = 900
    refresh_token_ttl: int = 604800
    ai_provider: str = "none"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
