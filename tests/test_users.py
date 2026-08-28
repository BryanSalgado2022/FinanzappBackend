from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_get_me_defaults_to_no_accent_color(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["color_acento"] is None


def test_patch_sets_accent_color_reflected_on_subsequent_get(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    patch = client.patch("/users/me", json={"color_acento": "azul"}, headers=headers)
    assert patch.status_code == 200, patch.text
    assert patch.json()["color_acento"] == "azul"

    get = client.get("/users/me", headers=headers)
    assert get.json()["color_acento"] == "azul"


def test_patch_rejects_invalid_accent_color(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.patch("/users/me", json={"color_acento": "azul"}, headers=headers)

    response = client.patch("/users/me", json={"color_acento": "no-existe"}, headers=headers)
    assert response.status_code == 422

    get = client.get("/users/me", headers=headers)
    assert get.json()["color_acento"] == "azul"


def test_patch_null_clears_accent_color(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.patch("/users/me", json={"color_acento": "morado"}, headers=headers)

    clear = client.patch("/users/me", json={"color_acento": None}, headers=headers)
    assert clear.status_code == 200, clear.text
    assert clear.json()["color_acento"] is None

    get = client.get("/users/me", headers=headers)
    assert get.json()["color_acento"] is None


def test_patch_empty_body_leaves_accent_color_unchanged(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.patch("/users/me", json={"color_acento": "rosa"}, headers=headers)

    response = client.patch("/users/me", json={}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["color_acento"] == "rosa"


def test_get_me_defaults_to_no_ahorros(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.get("/users/me", headers=headers)
    assert response.json()["ahorros"] is None


def test_patch_sets_and_clears_ahorros(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    patch = client.patch("/users/me", json={"ahorros": "1500000"}, headers=headers)
    assert patch.status_code == 200, patch.text
    assert patch.json()["ahorros"] == "1500000.00"

    clear = client.patch("/users/me", json={"ahorros": None}, headers=headers)
    assert clear.json()["ahorros"] is None


def test_users_me_scoped_to_authenticated_user(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    client.patch("/users/me", json={"color_acento": "rojo"}, headers=headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get("/users/me", headers=headers_b)
    assert response.json()["color_acento"] is None
    assert response.json()["email"] == "b@example.com"
