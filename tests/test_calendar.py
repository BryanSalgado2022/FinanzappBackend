import datetime

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_export_requires_auth(client: TestClient):
    response = client.get("/calendar/export")
    assert response.status_code == 401


def test_export_returns_ics_content(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.get("/calendar/export", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert response.text.startswith("BEGIN:VCALENDAR")
    assert response.text.strip().endswith("END:VCALENDAR")


def test_export_includes_gasto_within_window(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    today = datetime.date.today()
    client.post(
        "/gastos",
        json={"monto": "20000", "fecha": today.isoformat(), "descripcion": "Pizza"},
        headers=headers,
    )

    response = client.get("/calendar/export", headers=headers)
    assert "Pizza" in response.text


def test_export_excludes_gasto_outside_window(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    old_date = (datetime.date.today() - datetime.timedelta(days=400)).isoformat()
    client.post(
        "/gastos",
        json={"monto": "20000", "fecha": old_date, "descripcion": "MuyViejo"},
        headers=headers,
    )

    response = client.get("/calendar/export", headers=headers)
    assert "MuyViejo" not in response.text


def test_export_includes_tarea_within_window(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    today = datetime.date.today()
    client.post(
        "/tareas",
        json={"titulo": "LlamarBanco", "fecha": today.isoformat()},
        headers=headers,
    )

    response = client.get("/calendar/export", headers=headers)
    assert "LlamarBanco" in response.text


def test_export_includes_deudor_start_and_abono(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    today = datetime.date.today()
    deudor = client.post(
        "/deudores",
        json={"nombre": "PedroCalendario", "monto_total": "500000", "fecha": today.isoformat()},
        headers=headers,
    ).json()
    client.post(
        f"/deudores/{deudor['id']}/abonos",
        json={"monto": "50000", "fecha": today.isoformat()},
        headers=headers,
    )

    response = client.get("/calendar/export", headers=headers)
    assert "PedroCalendario" in response.text


def test_export_includes_concept_due_date(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    today = datetime.date.today()
    concept = client.post(
        "/concepts",
        json={"nombre": "InternetCalendario", "tipo": "gasto_fijo", "dia_vencimiento": 15},
        headers=headers,
    ).json()
    client.put(
        f"/concepts/{concept['id']}/entries/{today.year}/{today.month}",
        json={"monto_planeado": "50000.00"},
        headers=headers,
    )

    response = client.get("/calendar/export", headers=headers)
    assert "InternetCalendario" in response.text


def test_export_scoped_to_authenticated_user(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    today = datetime.date.today()
    client.post(
        "/gastos",
        json={"monto": "20000", "fecha": today.isoformat(), "descripcion": "SoloDeA"},
        headers=headers_a,
    )

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get("/calendar/export", headers=headers_b)
    assert "SoloDeA" not in response.text


def test_get_token_status_before_generation(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.get("/calendar/token", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["ics_token"] is None


def test_get_token_status_after_generation_does_not_change_it(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post("/calendar/token", headers=headers).json()["ics_token"]

    status_response = client.get("/calendar/token", headers=headers)
    assert status_response.json()["ics_token"] == created

    status_response_again = client.get("/calendar/token", headers=headers)
    assert status_response_again.json()["ics_token"] == created


def test_create_token_first_time(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post("/calendar/token", headers=headers)
    assert response.status_code == 200, response.text
    assert len(response.json()["ics_token"]) > 10


def test_regenerating_token_invalidates_previous(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    first = client.post("/calendar/token", headers=headers).json()["ics_token"]
    second = client.post("/calendar/token", headers=headers).json()["ics_token"]
    assert first != second

    stale = client.get(f"/calendar/subscribe/{first}")
    assert stale.status_code == 404

    fresh = client.get(f"/calendar/subscribe/{second}")
    assert fresh.status_code == 200


def test_subscribe_with_valid_token_requires_no_auth(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    token = client.post("/calendar/token", headers=headers).json()["ics_token"]

    response = client.get(f"/calendar/subscribe/{token}")
    assert response.status_code == 200
    assert response.text.startswith("BEGIN:VCALENDAR")


def test_subscribe_with_invalid_token(client: TestClient):
    response = client.get("/calendar/subscribe/not-a-real-token")
    assert response.status_code == 404


def test_subscribe_scoped_to_token_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    today = datetime.date.today()
    client.post(
        "/gastos",
        json={"monto": "20000", "fecha": today.isoformat(), "descripcion": "SecretoDeA"},
        headers=headers_a,
    )
    token_a = client.post("/calendar/token", headers=headers_a).json()["ics_token"]

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    token_b = client.post("/calendar/token", headers=headers_b).json()["ics_token"]

    response = client.get(f"/calendar/subscribe/{token_b}")
    assert "SecretoDeA" not in response.text

    response = client.get(f"/calendar/subscribe/{token_a}")
    assert "SecretoDeA" in response.text
