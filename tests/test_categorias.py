from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_create_categoria(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post("/categorias", json={"nombre": "Vivienda"}, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["nombre"] == "Vivienda"
    assert body["emoji"] is None


def test_create_categoria_with_emoji(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/categorias", json={"nombre": "Vivienda", "emoji": "🏠"}, headers=headers
    )
    assert response.status_code == 201, response.text
    assert response.json()["emoji"] == "🏠"


def test_create_categoria_rejects_invalid_emoji(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/categorias", json={"nombre": "Vivienda", "emoji": "🦄"}, headers=headers
    )
    assert response.status_code == 422


def test_create_categoria_is_idempotent_by_name_case_insensitive(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    first = client.post("/categorias", json={"nombre": "Creditos"}, headers=headers)
    second = client.post("/categorias", json={"nombre": "creditos"}, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    listed = client.get("/categorias", headers=headers)
    assert len(listed.json()) == 1


def test_list_categorias_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    client.post("/categorias", json={"nombre": "Vivienda"}, headers=headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    client.post("/categorias", json={"nombre": "Comida"}, headers=headers_b)

    response = client.get("/categorias", headers=headers_a)
    nombres = [c["nombre"] for c in response.json()]
    assert nombres == ["Vivienda"]


def test_get_categoria_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    created = client.post("/categorias", json={"nombre": "Vivienda"}, headers=headers_a)
    categoria_id = created.json()["id"]

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get(f"/categorias/{categoria_id}", headers=headers_b)
    assert response.status_code == 404


def test_update_categoria_propagates_to_concepts(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    categoria = client.post("/categorias", json={"nombre": "Creditos"}, headers=headers).json()
    concept = client.post(
        "/concepts",
        json={"nombre": "Lulo", "tipo": "deuda", "categoria_ids": [categoria["id"]]},
        headers=headers,
    ).json()
    assert concept["categorias"][0]["nombre"] == "Creditos"

    client.patch(
        f"/categorias/{categoria['id']}",
        json={"nombre": "Créditos", "emoji": "💳"},
        headers=headers,
    )

    refreshed = client.get(f"/concepts/{concept['id']}", headers=headers).json()
    assert refreshed["categorias"][0]["nombre"] == "Créditos"
    assert refreshed["categorias"][0]["emoji"] == "💳"


def test_update_categoria_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    categoria = client.post("/categorias", json={"nombre": "Vivienda"}, headers=headers_a).json()

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.patch(
        f"/categorias/{categoria['id']}", json={"nombre": "Hacked"}, headers=headers_b
    )
    assert response.status_code == 404


def test_delete_categoria_unassigns_without_error(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    categoria_a = client.post("/categorias", json={"nombre": "Vivienda"}, headers=headers).json()
    categoria_b = client.post("/categorias", json={"nombre": "Creditos"}, headers=headers).json()
    concept = client.post(
        "/concepts",
        json={
            "nombre": "Lulo",
            "tipo": "deuda",
            "categoria_ids": [categoria_a["id"], categoria_b["id"]],
        },
        headers=headers,
    ).json()

    delete = client.delete(f"/categorias/{categoria_a['id']}", headers=headers)
    assert delete.status_code == 204

    refreshed = client.get(f"/concepts/{concept['id']}", headers=headers).json()
    nombres = [c["nombre"] for c in refreshed["categorias"]]
    assert nombres == ["Creditos"]

    listed = client.get("/categorias", headers=headers)
    assert [c["nombre"] for c in listed.json()] == ["Creditos"]


def test_delete_categoria_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    categoria = client.post("/categorias", json={"nombre": "Vivienda"}, headers=headers_a).json()

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.delete(f"/categorias/{categoria['id']}", headers=headers_b)
    assert response.status_code == 404
