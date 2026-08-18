from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_create_gasto_with_required_fields_only(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/gastos",
        json={"monto": "20000", "fecha": "2026-03-05", "descripcion": "Pizza"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["monto"] == "20000.00"
    assert body["fecha"] == "2026-03-05"
    assert body["descripcion"] == "Pizza"
    assert body["categorias"] == []


def test_create_gasto_with_categoria_ids(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    categoria = client.post("/categorias", json={"nombre": "Comida"}, headers=headers).json()

    response = client.post(
        "/gastos",
        json={
            "monto": "20000",
            "fecha": "2026-03-05",
            "descripcion": "Pizza",
            "categoria_ids": [categoria["id"]],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert [c["nombre"] for c in response.json()["categorias"]] == ["Comida"]


def test_create_gasto_rejects_unknown_categoria_id(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/gastos",
        json={"monto": "20000", "fecha": "2026-03-05", "descripcion": "Pizza", "categoria_ids": [999999]},
        headers=headers,
    )
    assert response.status_code == 422


def test_create_gasto_rejects_categoria_id_from_another_user(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    categoria = client.post("/categorias", json={"nombre": "Comida"}, headers=headers_a).json()

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.post(
        "/gastos",
        json={
            "monto": "20000",
            "fecha": "2026-03-05",
            "descripcion": "Pizza",
            "categoria_ids": [categoria["id"]],
        },
        headers=headers_b,
    )
    assert response.status_code == 422


def test_list_gastos_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    client.post(
        "/gastos",
        json={"monto": "10000", "fecha": "2026-03-05", "descripcion": "Gasto A"},
        headers=headers_a,
    )

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    client.post(
        "/gastos",
        json={"monto": "20000", "fecha": "2026-03-05", "descripcion": "Gasto B"},
        headers=headers_b,
    )

    response = client.get("/gastos", headers=headers_a)
    descripciones = [g["descripcion"] for g in response.json()]
    assert descripciones == ["Gasto A"]


def test_list_gastos_filtered_by_year_month(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.post(
        "/gastos", json={"monto": "10000", "fecha": "2026-03-05", "descripcion": "Marzo"}, headers=headers
    )
    client.post(
        "/gastos", json={"monto": "20000", "fecha": "2026-04-10", "descripcion": "Abril"}, headers=headers
    )

    response = client.get("/gastos?anio=2026&mes=3", headers=headers)
    descripciones = [g["descripcion"] for g in response.json()]
    assert descripciones == ["Marzo"]


def test_get_gasto_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    created = client.post(
        "/gastos",
        json={"monto": "10000", "fecha": "2026-03-05", "descripcion": "Gasto A"},
        headers=headers_a,
    )
    gasto_id = created.json()["id"]

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get(f"/gastos/{gasto_id}", headers=headers_b)
    assert response.status_code == 404


def test_update_gasto_each_field_independently(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/gastos",
        json={"monto": "10000", "fecha": "2026-03-05", "descripcion": "Original"},
        headers=headers,
    )
    gasto_id = created.json()["id"]

    response = client.patch(f"/gastos/{gasto_id}", json={"descripcion": "Actualizado"}, headers=headers)
    assert response.json()["descripcion"] == "Actualizado"

    response = client.patch(f"/gastos/{gasto_id}", json={"monto": "15000"}, headers=headers)
    assert response.json()["monto"] == "15000.00"

    response = client.patch(f"/gastos/{gasto_id}", json={"fecha": "2026-02-01"}, headers=headers)
    assert response.json()["fecha"] == "2026-02-01"


def test_update_gasto_replaces_categoria_ids(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    cat_a = client.post("/categorias", json={"nombre": "Comida"}, headers=headers).json()
    cat_b = client.post("/categorias", json={"nombre": "Transporte"}, headers=headers).json()
    gasto = client.post(
        "/gastos",
        json={
            "monto": "10000",
            "fecha": "2026-03-05",
            "descripcion": "Gasto",
            "categoria_ids": [cat_a["id"]],
        },
        headers=headers,
    ).json()

    response = client.patch(
        f"/gastos/{gasto['id']}", json={"categoria_ids": [cat_b["id"]]}, headers=headers
    )
    assert response.status_code == 200, response.text
    assert [c["nombre"] for c in response.json()["categorias"]] == ["Transporte"]


def test_update_gasto_omitted_categoria_ids_leaves_assignments_unchanged(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    categoria = client.post("/categorias", json={"nombre": "Comida"}, headers=headers).json()
    gasto = client.post(
        "/gastos",
        json={
            "monto": "10000",
            "fecha": "2026-03-05",
            "descripcion": "Gasto",
            "categoria_ids": [categoria["id"]],
        },
        headers=headers,
    ).json()

    response = client.patch(f"/gastos/{gasto['id']}", json={"descripcion": "Gasto 2"}, headers=headers)
    assert response.status_code == 200, response.text
    assert [c["nombre"] for c in response.json()["categorias"]] == ["Comida"]


def test_update_gasto_empty_categoria_ids_clears_assignments(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    categoria = client.post("/categorias", json={"nombre": "Comida"}, headers=headers).json()
    gasto = client.post(
        "/gastos",
        json={
            "monto": "10000",
            "fecha": "2026-03-05",
            "descripcion": "Gasto",
            "categoria_ids": [categoria["id"]],
        },
        headers=headers,
    ).json()

    response = client.patch(f"/gastos/{gasto['id']}", json={"categoria_ids": []}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["categorias"] == []


def test_update_gasto_can_edit_past_month(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/gastos",
        json={"monto": "10000", "fecha": "2020-01-01", "descripcion": "Viejo"},
        headers=headers,
    )
    gasto_id = created.json()["id"]

    response = client.patch(f"/gastos/{gasto_id}", json={"monto": "12000"}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["monto"] == "12000.00"


def test_delete_gasto(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/gastos",
        json={"monto": "10000", "fecha": "2026-03-05", "descripcion": "Gasto"},
        headers=headers,
    )
    gasto_id = created.json()["id"]

    response = client.delete(f"/gastos/{gasto_id}", headers=headers)
    assert response.status_code == 204

    get = client.get(f"/gastos/{gasto_id}", headers=headers)
    assert get.status_code == 404
