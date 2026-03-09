from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "instockdb"

    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None

    DATABASE_URL: str | None = None
    SYNC_DATABASE_URL: str | None = None

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30天

    REDIS_HOST: str | None = None
    REDIS_PORT: int = 6379

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False

    LOG_LEVEL: str = "INFO"
    CORS_ALLOW_ORIGINS: str = "*"
    CORS_ALLOW_CREDENTIALS: bool = False
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"

    CRAWLER_PROXY_ENABLED: bool = False
    TUSHARE_TOKEN: str | None = None
    TUSHARE_HTTP_URL: str | None = None

    def get_async_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def get_sync_url(self) -> str:
        if self.SYNC_DATABASE_URL:
            return self.SYNC_DATABASE_URL
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def get_cors_origins(self) -> list[str]:
        raw = (self.CORS_ALLOW_ORIGINS or "").strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]

    def get_cors_methods(self) -> list[str]:
        raw = (self.CORS_ALLOW_METHODS or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [item.strip().upper() for item in raw.split(",") if item.strip()]

    def get_cors_headers(self) -> list[str]:
        raw = (self.CORS_ALLOW_HEADERS or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.SECRET_KEY == "your-secret-key-change-in-production":
        raise ValueError(
            "SECRET_KEY is using insecure default value. "
            "Please set SECRET_KEY in environment before starting the app."
        )
    if len(settings.SECRET_KEY) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters long.")
    return settings


settings = get_settings()
