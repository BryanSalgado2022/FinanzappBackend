from fastapi.testclient import TestClient
from sqlmodel import Session, select

import app.routers.auth as auth_router
from app.models.user import User
from tests.conftest import auth_headers


def test_first_time_sign_in_creates_user(client: TestClient, session: Session, monkeypatch):
    auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")

    users = session.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].google_sub == "google-1"
    assert users[0].email == "a@example.com"


def test_returning_sign_in_reuses_user(client: TestClient, session: Session, monkeypatch):
    auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")
    auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")

    users = session.exec(select(User)).all()
    assert len(users) == 1


def test_unauthenticated_request_rejected(client: TestClient):
    response = client.get("/concepts")
    assert response.status_code == 401


def test_user_cannot_access_another_users_concept(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    create = client.post(
        "/concepts", json={"nombre": "Internet", "tipo": "gasto_fijo"}, headers=headers_a
    )
    concept_id = create.json()["id"]

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get(f"/concepts/{concept_id}", headers=headers_b)
    assert response.status_code == 404


def test_dev_login_disabled_by_default(client: TestClient):
    response = client.post("/auth/dev-login")
    assert response.status_code == 404


def test_dev_login_works_when_explicitly_enabled(client: TestClient, monkeypatch):
    class FakeSettings:
        dev_mode = True

    monkeypatch.setattr(auth_router, "get_settings", lambda: FakeSettings())
    response = client.post("/auth/dev-login")
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_register_issues_token(client: TestClient, session: Session):
    response = client.post(
        "/auth/register",
        json={"nombre": "Ana", "email": "ana@example.com", "password": "supersecret"},
    )
    assert response.status_code == 201, response.text
    assert "access_token" in response.json()

    user = session.exec(select(User).where(User.email == "ana@example.com")).first()
    assert user is not None
    assert user.password_hash is not None
    assert user.password_hash != "supersecret"
    assert user.google_sub is None


def test_register_rejects_short_password(client: TestClient):
    response = client.post(
        "/auth/register",
        json={"nombre": "Ana", "email": "ana@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_register_rejects_email_already_used_by_google_account(
    client: TestClient, monkeypatch
):
    auth_headers(client, monkeypatch, sub="google-1", email="ana@example.com", name="Ana")

    response = client.post(
        "/auth/register",
        json={"nombre": "Ana", "email": "ana@example.com", "password": "supersecret"},
    )
    assert response.status_code == 409


def test_register_rejects_email_already_used_by_password_account(client: TestClient):
    client.post(
        "/auth/register",
        json={"nombre": "Ana", "email": "ana@example.com", "password": "supersecret"},
    )
    response = client.post(
        "/auth/register",
        json={"nombre": "Otra Ana", "email": "ana@example.com", "password": "differentpass"},
    )
    assert response.status_code == 409


def test_login_with_correct_credentials_issues_token(client: TestClient):
    client.post(
        "/auth/register",
        json={"nombre": "Ana", "email": "ana@example.com", "password": "supersecret"},
    )
    response = client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "supersecret"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_and_unknown_email_return_same_error(client: TestClient):
    client.post(
        "/auth/register",
        json={"nombre": "Ana", "email": "ana@example.com", "password": "supersecret"},
    )
    wrong_password = client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "wrongpassword"}
    )
    unknown_email = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever1"}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


def test_login_rejects_google_only_account(client: TestClient, monkeypatch):
    auth_headers(client, monkeypatch, sub="google-1", email="ana@example.com", name="Ana")

    response = client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "anypassword"}
    )
    assert response.status_code == 401


def test_google_sign_in_links_to_existing_password_account(
    client: TestClient, session: Session, monkeypatch
):
    client.post(
        "/auth/register",
        json={"nombre": "Ana", "email": "ana@example.com", "password": "supersecret"},
    )

    headers = auth_headers(client, monkeypatch, sub="google-1", email="ana@example.com", name="Ana")

    users = session.exec(select(User).where(User.email == "ana@example.com")).all()
    assert len(users) == 1
    assert users[0].google_sub == "google-1"
    assert users[0].password_hash is not None

    # The linked account is usable as the same identity for protected routes.
    response = client.get("/concepts", headers=headers)
    assert response.status_code == 200


def test_register_rate_limited(client: TestClient):
    for i in range(10):
        client.post(
            "/auth/register",
            json={"nombre": "X", "email": f"user{i}@example.com", "password": "supersecret"},
        )
    response = client.post(
        "/auth/register",
        json={"nombre": "X", "email": "oneMore@example.com", "password": "supersecret"},
    )
    assert response.status_code == 429


def test_login_rate_limited(client: TestClient):
    client.post(
        "/auth/register",
        json={"nombre": "Ana", "email": "ana@example.com", "password": "supersecret"},
    )
    for _ in range(10):
        client.post(
            "/auth/login", json={"email": "ana@example.com", "password": "wrongpassword"}
        )
    response = client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 429
