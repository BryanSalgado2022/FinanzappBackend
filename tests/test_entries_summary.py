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


def test_summary_uses_planned_amount_for_unpaid_entries(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    sueldo = client.post(
        "/concepts", json={"nombre": "Sueldo", "tipo": "ingreso"}, headers=headers
    ).json()
    client.put(
        f"/concepts/{sueldo['id']}/entries/2031/6",
        json={"monto_planeado": "10000000.00"},
        headers=headers,
    )

    summary = client.get("/summary", params={"anio": 2031, "mes": 6}, headers=headers).json()
    assert as_decimal(summary["total_ingresos"]) == Decimal("10000000.00")


def test_summary_uses_paid_amount_when_it_differs_from_planned(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    sueldo = client.post(
        "/concepts", json={"nombre": "Sueldo", "tipo": "ingreso"}, headers=headers
    ).json()
    # Planned 10.000.000, but only 9.500.000 actually arrived - reproduces
    # the reported scenario exactly.
    client.put(
        f"/concepts/{sueldo['id']}/entries/2031/6",
        json={"monto_planeado": "10000000.00", "monto_pagado": "9500000.00", "pagado": True},
        headers=headers,
    )

    summary = client.get("/summary", params={"anio": 2031, "mes": 6}, headers=headers).json()
    assert as_decimal(summary["total_ingresos"]) == Decimal("9500000.00")
    assert as_decimal(summary["balance_neto"]) == Decimal("9500000.00")


def test_summary_uses_paid_amount_for_overpaid_gasto_fijo(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    pago = client.post(
        "/concepts", json={"nombre": "Internet", "tipo": "gasto_fijo"}, headers=headers
    ).json()
    client.put(
        f"/concepts/{pago['id']}/entries/2031/6",
        json={"monto_planeado": "50000.00", "monto_pagado": "55000.00", "pagado": True},
        headers=headers,
    )

    summary = client.get("/summary", params={"anio": 2031, "mes": 6}, headers=headers).json()
    assert as_decimal(summary["total_gastos"]) == Decimal("55000.00")


def test_summary_includes_abono_interes_in_the_requested_month(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = client.post(
        "/deudores",
        json={"nombre": "Pedro", "monto_total": "500000", "fecha": "2031-01-01"},
        headers=headers,
    ).json()
    client.post(
        f"/deudores/{deudor['id']}/abonos",
        json={"monto": "110000", "fecha": "2031-03-10", "interes": "10000"},
        headers=headers,
    )

    summary = client.get("/summary", params={"anio": 2031, "mes": 3}, headers=headers).json()
    assert as_decimal(summary["total_ingresos"]) == Decimal("10000.00")
    assert as_decimal(summary["balance_neto"]) == Decimal("10000.00")


def test_summary_ignores_abono_interes_outside_the_requested_month(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = client.post(
        "/deudores",
        json={"nombre": "Pedro", "monto_total": "500000", "fecha": "2031-01-01"},
        headers=headers,
    ).json()
    client.post(
        f"/deudores/{deudor['id']}/abonos",
        json={"monto": "110000", "fecha": "2031-04-10", "interes": "10000"},
        headers=headers,
    )

    summary = client.get("/summary", params={"anio": 2031, "mes": 3}, headers=headers).json()
    assert as_decimal(summary["total_ingresos"]) == Decimal("0")


def test_summary_unaffected_by_abono_with_no_interes(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = client.post(
        "/deudores",
        json={"nombre": "Pedro", "monto_total": "500000", "fecha": "2031-01-01"},
        headers=headers,
    ).json()
    client.post(
        f"/deudores/{deudor['id']}/abonos",
        json={"monto": "110000", "fecha": "2031-03-10"},
        headers=headers,
    )

    summary = client.get("/summary", params={"anio": 2031, "mes": 3}, headers=headers).json()
    assert as_decimal(summary["total_ingresos"]) == Decimal("0")


def test_summary_includes_paid_cuota_deudor_interes_in_the_month_it_was_paid(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    # A schedule anchored to a past/future fecha (2031-01) so the cuota's own
    # scheduled anio/mes never coincides with today - marking it paid records
    # fecha_pago as today, so income must show up in today's month, not 2031-01.
    deudor = client.post(
        "/deudores",
        json={
            "nombre": "Pedro",
            "monto_total": "1000000.00",
            "fecha": "2031-01-01",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    ).json()
    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    primera = next(c for c in cuotas if c["anio"] == 2031 and c["mes"] == 1)

    client.patch(
        f"/deudores/{deudor['id']}/cuotas/2031/1",
        json={"monto_pagado": primera["monto_planeado"], "pagado": True},
        headers=headers,
    )

    today = datetime.date.today()
    summary_scheduled_month = client.get(
        "/summary", params={"anio": 2031, "mes": 1}, headers=headers
    ).json()
    assert as_decimal(summary_scheduled_month["total_ingresos"]) == Decimal("0")

    summary_payment_month = client.get(
        "/summary", params={"anio": today.year, "mes": today.month}, headers=headers
    ).json()
    assert as_decimal(summary_payment_month["total_ingresos"]) == as_decimal(primera["interes"])


def test_summary_unaffected_by_unpaid_cuota_deudor(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = client.post(
        "/deudores",
        json={
            "nombre": "Pedro",
            "monto_total": "1000000.00",
            "fecha": "2031-01-01",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    ).json()

    summary = client.get("/summary", params={"anio": 2031, "mes": 1}, headers=headers).json()
    assert as_decimal(summary["total_ingresos"]) == Decimal("0")


def test_summary_unaffected_by_cuota_deudor_principal(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = client.post(
        "/deudores",
        json={
            "nombre": "Pedro",
            "monto_total": "1000000.00",
            "fecha": "2031-01-01",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    ).json()
    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    primera = next(c for c in cuotas if c["anio"] == 2031 and c["mes"] == 1)

    client.patch(
        f"/deudores/{deudor['id']}/cuotas/2031/1",
        json={"monto_pagado": primera["monto_planeado"], "pagado": True},
        headers=headers,
    )

    today = datetime.date.today()
    summary = client.get(
        "/summary", params={"anio": today.year, "mes": today.month}, headers=headers
    ).json()
    # Only the interest portion counts, not the full monto_pagado (which
    # includes principal).
    assert as_decimal(summary["total_ingresos"]) == as_decimal(primera["interes"])
    assert as_decimal(summary["total_ingresos"]) < as_decimal(primera["monto_planeado"])


def test_fecha_pago_set_on_pagado_transition_and_cleared_on_unpaid(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    concept = client.post(
        "/concepts", json={"nombre": "Netflix", "tipo": "gasto_fijo"}, headers=headers
    ).json()
    concept_id = concept["id"]
    today = datetime.date.today().isoformat()

    unpaid = client.put(
        f"/concepts/{concept_id}/entries/2032/1",
        json={"monto_planeado": "50000.00"},
        headers=headers,
    )
    assert unpaid.json()["fecha_pago"] is None

    paid = client.put(
        f"/concepts/{concept_id}/entries/2032/1",
        json={"monto_planeado": "50000.00", "pagado": True},
        headers=headers,
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["fecha_pago"] == today

    # Re-saving an already-paid entry (correcting monto_pagado) must not
    # bump fecha_pago again.
    edited = client.put(
        f"/concepts/{concept_id}/entries/2032/1",
        json={"monto_planeado": "50000.00", "monto_pagado": "45000.00", "pagado": True},
        headers=headers,
    )
    assert edited.json()["fecha_pago"] == today

    unpaid_again = client.put(
        f"/concepts/{concept_id}/entries/2032/1",
        json={"monto_planeado": "50000.00", "pagado": False},
        headers=headers,
    )
    assert unpaid_again.json()["fecha_pago"] is None
