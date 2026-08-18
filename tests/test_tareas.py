from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_create_tarea_with_just_title(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post("/tareas", json={"titulo": "Pagar la luz"}, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["titulo"] == "Pagar la luz"
    assert body["emoji"] is None
    assert body["fecha"] is None
    assert body["hora"] is None
    assert body["nota"] is None
    assert body["completada"] is False
    assert body["vencida"] is False


def test_create_tarea_with_all_fields(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/tareas",
        json={
            "titulo": "Cita con el banco",
            "emoji": "🏦",
            "fecha": "2030-01-15",
            "hora": "10:30:00",
            "nota": "Llevar cédula",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["titulo"] == "Cita con el banco"
    assert body["emoji"] == "🏦"
    assert body["fecha"] == "2030-01-15"
    assert body["hora"] == "10:30:00"
    assert body["nota"] == "Llevar cédula"


def test_create_tarea_rejects_invalid_emoji(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/tareas", json={"titulo": "Test", "emoji": "🦄"}, headers=headers
    )
    assert response.status_code == 422


def test_list_tareas_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    client.post("/tareas", json={"titulo": "Tarea A"}, headers=headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    client.post("/tareas", json={"titulo": "Tarea B"}, headers=headers_b)

    response = client.get("/tareas", headers=headers_a)
    titulos = [t["titulo"] for t in response.json()]
    assert titulos == ["Tarea A"]


def test_get_tarea_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    created = client.post("/tareas", json={"titulo": "Tarea A"}, headers=headers_a)
    tarea_id = created.json()["id"]

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get(f"/tareas/{tarea_id}", headers=headers_b)
    assert response.status_code == 404


def test_update_tarea_each_field_independently(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post("/tareas", json={"titulo": "Original"}, headers=headers)
    tarea_id = created.json()["id"]

    response = client.patch(f"/tareas/{tarea_id}", json={"titulo": "Actualizado"}, headers=headers)
    assert response.json()["titulo"] == "Actualizado"

    response = client.patch(f"/tareas/{tarea_id}", json={"emoji": "⏰"}, headers=headers)
    assert response.json()["emoji"] == "⏰"

    response = client.patch(f"/tareas/{tarea_id}", json={"fecha": "2030-06-01"}, headers=headers)
    assert response.json()["fecha"] == "2030-06-01"

    response = client.patch(f"/tareas/{tarea_id}", json={"hora": "08:00:00"}, headers=headers)
    assert response.json()["hora"] == "08:00:00"

    response = client.patch(f"/tareas/{tarea_id}", json={"nota": "una nota"}, headers=headers)
    assert response.json()["nota"] == "una nota"


def test_toggle_completada(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post("/tareas", json={"titulo": "Test"}, headers=headers)
    tarea_id = created.json()["id"]

    response = client.patch(f"/tareas/{tarea_id}", json={"completada": True}, headers=headers)
    assert response.json()["completada"] is True

    response = client.patch(f"/tareas/{tarea_id}", json={"completada": False}, headers=headers)
    assert response.json()["completada"] is False


def test_update_tarea_rejects_invalid_emoji(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post("/tareas", json={"titulo": "Test"}, headers=headers)
    tarea_id = created.json()["id"]

    response = client.patch(f"/tareas/{tarea_id}", json={"emoji": "🦄"}, headers=headers)
    assert response.status_code == 422


def test_delete_tarea_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    created = client.post("/tareas", json={"titulo": "Tarea A"}, headers=headers_a)
    tarea_id = created.json()["id"]

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.delete(f"/tareas/{tarea_id}", headers=headers_b)
    assert response.status_code == 404


def test_delete_tarea(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post("/tareas", json={"titulo": "Tarea"}, headers=headers)
    tarea_id = created.json()["id"]

    response = client.delete(f"/tareas/{tarea_id}", headers=headers)
    assert response.status_code == 204

    get = client.get(f"/tareas/{tarea_id}", headers=headers)
    assert get.status_code == 404


def test_vencida_true_when_past_date_and_not_completed(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/tareas", json={"titulo": "Vencida", "fecha": "2020-01-01"}, headers=headers
    )
    assert created.json()["vencida"] is True


def test_vencida_false_when_past_date_and_completed(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/tareas",
        json={"titulo": "Vencida pero completada", "fecha": "2020-01-01"},
        headers=headers,
    )
    tarea_id = created.json()["id"]

    response = client.patch(f"/tareas/{tarea_id}", json={"completada": True}, headers=headers)
    assert response.json()["vencida"] is False


def test_vencida_false_when_no_date(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post("/tareas", json={"titulo": "Sin fecha"}, headers=headers)
    assert created.json()["vencida"] is False


def test_vencida_false_when_future_date(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/tareas", json={"titulo": "Futura", "fecha": "2030-01-01"}, headers=headers
    )
    assert created.json()["vencida"] is False
