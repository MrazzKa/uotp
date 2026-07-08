from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://192.168.0.196:5173"
    database_url: str = "postgresql+asyncpg://uotp:uotp@localhost:5432/uotp"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_public_endpoint: str = "http://localhost:9000"
    minio_root_user: str = "uotp_minio"
    minio_root_password: str = "uotp_minio_password"
    minio_bucket: str = "uotp-files"
    minio_secure: bool = False
    jwt_secret: str = Field(default="change-me-in-real-env-with-at-least-32-bytes")
    jwt_algorithm: str = "HS256"
    access_token_ttl: int = 900
    refresh_token_ttl: int = 604800
    ai_provider: str = "none"
    # Голосовой модуль: распознавание речи и разбор задачи через OpenAI.
    # Пусто = модуль выключен (эндпоинт вернёт 503). Ключ задаётся в .env.
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_stt_model: str = "whisper-1"
    openai_parse_model: str = "gpt-4o-mini"
    # When true, ADMIN accounts without an enrolled TOTP secret are denied login
    # (enable after admins have completed 2FA enrollment).
    admin_2fa_required: bool = False
    # Login brute-force protection.
    login_rate_limit: int = 10
    login_rate_window: int = 60
    # Max upload size per attachment file (bytes) and allowed MIME prefixes.
    max_upload_bytes: int = 15 * 1024 * 1024
    attachment_url_ttl: int = 600

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
