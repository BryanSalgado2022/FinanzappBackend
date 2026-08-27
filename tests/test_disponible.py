from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_disponible_unset_before_configuration(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.get("/summary/disponible", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["disponible"] is None
    assert response.json()["saldo_disponible_fecha"] is None


def test_disponible_equals_baseline_with_no_movements(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.patch("/users/me", json={"saldo_disponible_inicial": "1000000"}, headers=headers)

    response = client.get("/summary/disponible", headers=headers)
    assert as_decimal(response.json()["disponible"]) == Decimal("1000000.00")


def test_disponible_includes_paid_ingreso_monto_pagado(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.patch("/users/me", json={"saldo_disponible_inicial": "0"}, headers=headers)

    sueldo = client.post(
        "/concepts", json={"nombre": "Sueldo", "tipo": "ingreso"}, headers=headers
    ).json()
    client.put(
        f"/concepts/{sueldo['id']}/entries/2031/6",
        json={"monto_planeado": "3000000.00", "monto_pagado": "3000000.00", "pagado": True},
        headers=headers,
    )

    response = client.get("/summary/disponible", headers=headers)
    assert as_decimal(response.json()["disponible"]) == Decimal("3000000.00")


def test_disponible_ignores_unpaid_ingreso(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.patch("/users/me", json={"saldo_disponible_inicial": "0"}, headers=headers)

    sueldo = client.post(
        "/concepts", json={"nombre": "Sueldo", "tipo": "ingreso"}, headers=headers
    ).json()
    client.put(
        f"/concepts/{sueldo['id']}/entries/2031/6",
        json={"monto_planeado": "3000000.00"},
        headers=headers,
    )

    response = client.get("/summary/disponible", headers=headers)
    assert as_decimal(response.json()["disponible"]) == Decimal("0")


def test_disponible_partial_payment_only_reduces_by_amount_actually_paid(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    client.patch("/users/me", json={"saldo_disponible_inicial": "1000000"}, headers=headers)

    deuda = client.post(
        "/concepts", json={"nombre": "JFK", "tipo": "deuda", "valor_total": "5000000"},
        headers=headers,
    ).json()
    client.put(
        f"/concepts/{deuda['id']}/entries/2031/6",
        json={"monto_planeado": "100000.00", "monto_pagado": "50000.00", "pagado": True},
        headers=headers,
    )

    response = client.get("/summary/disponible", headers=headers)
    # Only the 50.000 actually paid reduces Disponible, not the 100.000 planned.
    assert as_decimal(response.json()["disponible"]) == Decimal("950000.00")


def test_disponible_reduced_by_gasto_variable(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    today = client.patch(
        "/users/me", json={"saldo_disponible_inicial": "1000000"}, headers=headers
    ).json()["saldo_disponible_fecha"]
    client.post(
        "/gastos", json={"monto": "30000", "fecha": today, "descripcion": "Mercado"},
        headers=headers,
    )

    response = client.get("/summary/disponible", headers=headers)
    assert as_decimal(response.json()["disponible"]) == Decimal("970000.00")


def test_disponible_ignores_gasto_before_baseline(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    client.post(
        "/gastos", json={"monto": "30000", "fecha": "2020-01-01", "descripcion": "Viejo"},
        headers=headers,
    )
    client.patch("/users/me", json={"saldo_disponible_inicial": "1000000"}, headers=headers)

    response = client.get("/summary/disponible", headers=headers)
    assert as_decimal(response.json()["disponible"]) == Decimal("1000000.00")


def test_disponible_includes_abono_interes(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    today = client.patch(
        "/users/me", json={"saldo_disponible_inicial": "0"}, headers=headers
    ).json()["saldo_disponible_fecha"]
    deudor = client.post(
        "/deudores", json={"nombre": "Pedro", "monto_total": "500000", "fecha": "2031-01-01"},
        headers=headers,
    ).json()
    client.post(
        f"/deudores/{deudor['id']}/abonos",
        json={"monto": "110000", "fecha": today, "interes": "10000"},
        headers=headers,
    )

    response = client.get("/summary/disponible", headers=headers)
    assert as_decimal(response.json()["disponible"]) == Decimal("10000.00")


def test_disponible_ignores_abono_interes_before_baseline(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = client.post(
        "/deudores", json={"nombre": "Pedro", "monto_total": "500000", "fecha": "2020-01-01"},
        headers=headers,
    ).json()
    client.post(
        f"/deudores/{deudor['id']}/abonos",
        json={"monto": "110000", "fecha": "2020-02-01", "interes": "10000"},
        headers=headers,
    )
    client.patch("/users/me", json={"saldo_disponible_inicial": "0"}, headers=headers)

    response = client.get("/summary/disponible", headers=headers)
    assert as_decimal(response.json()["disponible"]) == Decimal("0")


def test_disponible_scoped_to_authenticated_user(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    client.patch("/users/me", json={"saldo_disponible_inicial": "1000000"}, headers=headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get("/summary/disponible", headers=headers_b)
    assert response.json()["disponible"] is None
