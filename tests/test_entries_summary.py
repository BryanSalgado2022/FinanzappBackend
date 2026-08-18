import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_auto_generation_on_create_fills_rest_of_year(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    today = datetime.date.today()

    create = client.post(
        "/concepts",
        json={"nombre": "Internet", "tipo": "gasto_fijo", "monto_planeado": "50000.00"},
        headers=headers,
    )
    concept_id = create.json()["id"]

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    months = {e["mes"]: e["monto_planeado"] for e in entries if e["anio"] == today.year}
    for mes in range(today.month, 13):
        assert as_decimal(months[mes]) == Decimal("50000.00")


def test_edit_current_month_fills_forward_without_overwriting_customized_months(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    today = datetime.date.today()
    if today.month >= 11:
        pytest.skip("needs at least two free months after the current one to exercise this case")

    create = client.post(
        "/concepts", json={"nombre": "Suscripcion", "tipo": "gasto_fijo"}, headers=headers
    )
    concept_id = create.json()["id"]

    custom_month = today.month + 2
    client.put(
        f"/concepts/{concept_id}/entries/{today.year}/{custom_month}",
        json={"monto_planeado": "99999.00"},
        headers=headers,
    )

    client.put(
        f"/concepts/{concept_id}/entries/{today.year}/{today.month}",
        json={"monto_planeado": "10000.00"},
        headers=headers,
    )

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    months = {e["mes"]: as_decimal(e["monto_planeado"]) for e in entries if e["anio"] == today.year}
    assert months[custom_month] == Decimal("99999.00")
    assert months[today.month] == Decimal("10000.00")
    assert months[today.month + 1] == Decimal("10000.00")


def test_planned_and_paid_amounts_can_differ(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={"nombre": "JFK", "tipo": "deuda", "valor_total": "38000000.00"},
        headers=headers,
    )
    concept_id = create.json()["id"]

    response = client.put(
        f"/concepts/{concept_id}/entries/2030/1",
        json={"monto_planeado": "1000000.00", "monto_pagado": "500000.00", "pagado": True},
        headers=headers,
    )
    body = response.json()
    assert as_decimal(body["monto_planeado"]) == Decimal("1000000.00")
    assert as_decimal(body["monto_pagado"]) == Decimal("500000.00")
    assert body["pagado"] is True


def test_monthly_summary_matches_verified_spreadsheet_numbers(client: TestClient, monkeypatch):
    """Regression test for the balance_neto formula, checked against the
    user's real spreadsheet: July 7,500,000 - 6,944,500 = 555,500;
    August 7,500,000 - 10,593,500 = -3,093,500."""
    headers = _headers(client, monkeypatch)

    sueldo = client.post("/concepts", json={"nombre": "Sueldo", "tipo": "ingreso"}, headers=headers).json()
    allizz = client.post("/concepts", json={"nombre": "Allizz", "tipo": "ingreso"}, headers=headers).json()
    gastos = client.post(
        "/concepts", json={"nombre": "GastosDelMes", "tipo": "gasto_fijo"}, headers=headers
    ).json()

    for mes, monto_gastos in ((7, "6944500.00"), (8, "10593500.00")):
        client.put(
            f"/concepts/{sueldo['id']}/entries/2030/{mes}",
            json={"monto_planeado": "7400000.00"},
            headers=headers,
        )
        client.put(
            f"/concepts/{allizz['id']}/entries/2030/{mes}",
            json={"monto_planeado": "100000.00"},
            headers=headers,
        )
        client.put(
            f"/concepts/{gastos['id']}/entries/2030/{mes}",
            json={"monto_planeado": monto_gastos},
            headers=headers,
        )

    july = client.get("/summary", params={"anio": 2030, "mes": 7}, headers=headers).json()
    assert as_decimal(july["balance_neto"]) == Decimal("555500.00")

    august = client.get("/summary", params={"anio": 2030, "mes": 8}, headers=headers).json()
    assert as_decimal(august["balance_neto"]) == Decimal("-3093500.00")


def test_summary_with_no_entries_returns_zero(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.get("/summary", params={"anio": 1999, "mes": 1}, headers=headers)
    assert as_decimal(response.json()["balance_neto"]) == Decimal("0")


def test_summary_subtracts_variable_expenses_in_the_requested_month(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    sueldo = client.post("/concepts", json={"nombre": "Sueldo", "tipo": "ingreso"}, headers=headers).json()
    client.put(
        f"/concepts/{sueldo['id']}/entries/2031/3",
        json={"monto_planeado": "1000000.00"},
        headers=headers,
    )
    client.post(
        "/gastos", json={"monto": "20000", "fecha": "2031-03-05", "descripcion": "Pizza"}, headers=headers
    )

    summary = client.get("/summary", params={"anio": 2031, "mes": 3}, headers=headers).json()
    assert as_decimal(summary["total_gastos"]) == Decimal("20000.00")
    assert as_decimal(summary["balance_neto"]) == Decimal("980000.00")


def test_summary_ignores_variable_expenses_outside_the_requested_month(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    client.post(
        "/gastos", json={"monto": "20000", "fecha": "2031-04-05", "descripcion": "Pizza"}, headers=headers
    )

    summary = client.get("/summary", params={"anio": 2031, "mes": 3}, headers=headers).json()
    assert as_decimal(summary["total_gastos"]) == Decimal("0")
    assert as_decimal(summary["balance_neto"]) == Decimal("0")
