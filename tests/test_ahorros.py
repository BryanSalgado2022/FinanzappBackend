from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_create_aporte(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/ahorros", json={"monto": "100000", "fecha": "2026-01-01", "tipo": "aporte"}, headers=headers
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["monto"] == "100000.00"
    assert body["tipo"] == "aporte"


def test_create_retiro(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/ahorros", json={"monto": "30000", "fecha": "2026-01-05", "tipo": "retiro"}, headers=headers
    )
    assert response.status_code == 201, response.text
    assert response.json()["tipo"] == "retiro"


def test_running_balance_reflects_mix_of_aporte_and_retiro(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.post(
        "/ahorros", json={"monto": "100000", "fecha": "2026-01-01", "tipo": "aporte"}, headers=headers
    )
    client.post(
        "/ahorros", json={"monto": "30000", "fecha": "2026-01-05", "tipo": "retiro"}, headers=headers
    )
    client.post(
        "/ahorros", json={"monto": "20000", "fecha": "2026-01-10", "tipo": "aporte"}, headers=headers
    )

    response = client.get("/users/me", headers=headers)
    assert as_decimal(response.json()["ahorros"]) == as_decimal("90000")


def test_running_balance_with_no_entries_is_zero(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.get("/users/me", headers=headers)
    assert as_decimal(response.json()["ahorros"]) == as_decimal("0")


def test_list_aportes_ordered_by_fecha_descending(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.post(
        "/ahorros", json={"monto": "10000", "fecha": "2026-01-01", "tipo": "aporte"}, headers=headers
    )
    client.post(
        "/ahorros", json={"monto": "20000", "fecha": "2026-03-01", "tipo": "aporte"}, headers=headers
    )
    client.post(
        "/ahorros", json={"monto": "30000", "fecha": "2026-02-01", "tipo": "aporte"}, headers=headers
    )

    response = client.get("/ahorros", headers=headers)
    fechas = [a["fecha"] for a in response.json()]
    assert fechas == ["2026-03-01", "2026-02-01", "2026-01-01"]


def test_list_aportes_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    client.post(
        "/ahorros", json={"monto": "10000", "fecha": "2026-01-01", "tipo": "aporte"}, headers=headers_a
    )

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get("/ahorros", headers=headers_b)
    assert response.json() == []


def test_delete_aporte_updates_balance(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/ahorros", json={"monto": "100000", "fecha": "2026-01-01", "tipo": "aporte"}, headers=headers
    )
    aporte_id = created.json()["id"]

    response = client.delete(f"/ahorros/{aporte_id}", headers=headers)
    assert response.status_code == 204

    balance = client.get("/users/me", headers=headers)
    assert as_decimal(balance.json()["ahorros"]) == as_decimal("0")


def test_delete_aporte_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    created = client.post(
        "/ahorros", json={"monto": "10000", "fecha": "2026-01-01", "tipo": "aporte"}, headers=headers_a
    )
    aporte_id = created.json()["id"]

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.delete(f"/ahorros/{aporte_id}", headers=headers_b)
    assert response.status_code == 404


def test_retiro_does_not_affect_monthly_summary(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.post(
        "/ahorros", json={"monto": "100000", "fecha": "2026-03-10", "tipo": "retiro"}, headers=headers
    )

    summary = client.get("/summary", params={"anio": 2026, "mes": 3}, headers=headers).json()
    assert as_decimal(summary["total_ingresos"]) == as_decimal("0")
    assert as_decimal(summary["total_gastos"]) == as_decimal("0")
    assert as_decimal(summary["balance_neto"]) == as_decimal("0")


def test_aporte_does_not_affect_monthly_summary(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.post(
        "/ahorros", json={"monto": "100000", "fecha": "2026-03-10", "tipo": "aporte"}, headers=headers
    )

    summary = client.get("/summary", params={"anio": 2026, "mes": 3}, headers=headers).json()
    assert as_decimal(summary["total_ingresos"]) == as_decimal("0")
    assert as_decimal(summary["total_gastos"]) == as_decimal("0")
    assert as_decimal(summary["balance_neto"]) == as_decimal("0")
