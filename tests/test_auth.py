from fastapi.testclient import TestClient
from sqlmodel import Session, select

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
