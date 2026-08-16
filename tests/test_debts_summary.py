from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_debts_summary_with_no_debts(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.get("/debts/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["numero_deudas"] == 0
    assert as_decimal(body["total_adeudado"]) == Decimal("0")
    assert body["composicion"] == []


def test_debts_summary_aggregates_multiple_debts(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    d1 = client.post(
        "/concepts", json={"nombre": "Deuda A", "tipo": "deuda", "valor_total": "1000000.00"},
        headers=headers,
    ).json()
    d2 = client.post(
        "/concepts", json={"nombre": "Deuda B", "tipo": "deuda", "valor_total": "500000.00"},
        headers=headers,
    ).json()

    client.put(
        f"/concepts/{d1['id']}/entries/2030/1",
        json={"monto_planeado": "1000000.00", "monto_pagado": "1000000.00", "pagado": True},
        headers=headers,
    )
    client.put(
        f"/concepts/{d2['id']}/entries/2030/1",
        json={"monto_planeado": "500000.00", "monto_pagado": "100000.00", "pagado": True},
        headers=headers,
    )

    response = client.get("/debts/summary", headers=headers)
    body = response.json()
    assert body["numero_deudas"] == 2
    assert as_decimal(body["total_adeudado"]) == Decimal("1500000.00")
    assert as_decimal(body["total_pagado"]) == Decimal("1100000.00")
    assert as_decimal(body["saldo_total_restante"]) == Decimal("400000.00")
    assert len(body["composicion"]) == 2


def test_debts_summary_scoped_to_user(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    client.post(
        "/concepts", json={"nombre": "Deuda A", "tipo": "deuda", "valor_total": "1000000.00"},
        headers=headers_a,
    )

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get("/debts/summary", headers=headers_b)
    assert response.json()["numero_deudas"] == 0


def test_annual_trend_returns_twelve_months(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.get("/summary/annual", params={"anio": 2030}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["meses"]) == 12
    assert [m["mes"] for m in body["meses"]] == list(range(1, 13))


def test_annual_trend_reflects_entries_and_zero_for_empty_months(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    sueldo = client.post(
        "/concepts", json={"nombre": "Sueldo", "tipo": "ingreso"}, headers=headers
    ).json()
    client.put(
        f"/concepts/{sueldo['id']}/entries/2031/3",
        json={"monto_planeado": "5000000.00"},
        headers=headers,
    )

    response = client.get("/summary/annual", params={"anio": 2031}, headers=headers)
    meses = {m["mes"]: m for m in response.json()["meses"]}
    assert as_decimal(meses[3]["total_ingresos"]) == Decimal("5000000.00")
    assert as_decimal(meses[1]["total_ingresos"]) == Decimal("0")
