import os
from collections.abc import Generator
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("JWT_SECRET", "test-secret")
# Without this, Settings falls back to reading the real .env file's DEV_MODE
# value (pydantic-settings env_file fallback), coupling test behavior to
# whatever the developer's local .env happens to have set.
os.environ["DEV_MODE"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app
from app.services.rate_limit import reset_rate_limits


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    # The rate limiter's counters live at module scope (see
    # app/services/rate_limit.py) - without this, one test's login/register
    # attempts could trip another test's limit.
    reset_rate_limits()
    yield


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def auth_headers(client: TestClient, monkeypatch, *, sub: str, email: str, name: str) -> dict[str, str]:
    """Signs a user in by faking Google's ID-token verification (no real
    Google credentials involved) and returns bearer headers for that user."""
    import app.routers.auth as auth_router

    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda token: {"sub": sub, "email": email, "name": name},
    )
    response = client.post("/auth/google", json={"id_token": "fake-token"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def as_decimal(value) -> Decimal:
    """Compares JSON-serialized money fields regardless of whether they came
    back as a JSON string or a number."""
    return Decimal(str(value))
