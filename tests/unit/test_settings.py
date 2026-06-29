from app.config.settings import Settings


def test_settings_support_database_url_and_cors_override(monkeypatch):
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.delenv("POSTGRES_PORT", raising=False)
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    monkeypatch.delenv("POSTGRES_USER", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.internal:5432/app")
    monkeypatch.setenv("REDIS_URL", "redis://redis.internal:6379/0")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://example.com,https://app.example.com")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("JWT_SECRET", "jwt-secret")

    settings = Settings(_env_file=None)

    assert settings.database.async_url.startswith("postgresql+asyncpg://user:pass@db.internal:5432/app")
    assert settings.redis.url == "redis://redis.internal:6379/0"
    assert settings.allowed_origins == ["https://example.com", "https://app.example.com"]
    assert settings.secret_key == "test-secret"
    assert settings.jwt.secret_key == "jwt-secret"
