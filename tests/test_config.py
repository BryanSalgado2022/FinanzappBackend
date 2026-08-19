from app.config import Settings


def _settings(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        google_client_id="test-client-id",
        jwt_secret="test-secret",
    )


def test_bare_postgres_scheme_gets_psycopg_driver():
    # Railway (and Heroku-style platforms) inject DATABASE_URL without a
    # driver - SQLAlchemy would otherwise default to psycopg2, which isn't
    # installed (this project uses psycopg v3).
    s = _settings("postgres://user:pass@host:5432/db")
    assert s.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_bare_postgresql_scheme_gets_psycopg_driver():
    s = _settings("postgresql://user:pass@host:5432/db")
    assert s.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_explicit_driver_is_left_untouched():
    s = _settings("postgresql+psycopg://user:pass@host:5432/db")
    assert s.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_sqlite_url_is_left_untouched():
    s = _settings("sqlite://")
    assert s.database_url == "sqlite://"
