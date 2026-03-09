import pytest

from app.config import Settings, get_settings


def test_settings_build_database_urls_from_components():
    settings = Settings(
        SECRET_KEY="x" * 32,
        DB_HOST="db",
        DB_PORT=5433,
        DB_USER="instock",
        DB_PASSWORD="password",
        DB_NAME="stocks",
    )

    assert settings.get_async_url() == "postgresql+asyncpg://instock:password@db:5433/stocks"
    assert settings.get_sync_url() == "postgresql+psycopg2://instock:password@db:5433/stocks"


def test_settings_prefer_explicit_database_urls():
    settings = Settings(
        SECRET_KEY="x" * 32,
        DATABASE_URL="postgresql+asyncpg://custom-async",
        SYNC_DATABASE_URL="postgresql+psycopg2://custom-sync",
    )

    assert settings.get_async_url() == "postgresql+asyncpg://custom-async"
    assert settings.get_sync_url() == "postgresql+psycopg2://custom-sync"


def test_settings_parse_cors_fields():
    settings = Settings(
        SECRET_KEY="x" * 32,
        CORS_ALLOW_ORIGINS="https://a.example.com, https://b.example.com",
        CORS_ALLOW_METHODS="get,post",
        CORS_ALLOW_HEADERS="authorization, content-type",
    )

    assert settings.get_cors_origins() == [
        "https://a.example.com",
        "https://b.example.com",
    ]
    assert settings.get_cors_methods() == ["GET", "POST"]
    assert settings.get_cors_headers() == ["authorization", "content-type"]


def test_get_settings_rejects_default_secret(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("SECRET_KEY", "your-secret-key-change-in-production")

    with pytest.raises(ValueError, match="insecure default value"):
        get_settings()

    get_settings.cache_clear()


def test_get_settings_rejects_short_secret(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("SECRET_KEY", "short-secret")

    with pytest.raises(ValueError, match="at least 32 characters"):
        get_settings()

    get_settings.cache_clear()
