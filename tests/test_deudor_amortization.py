from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_create_amortized_deudor_saves_terms_and_cuota_fija(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
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
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["numero_cuotas"] == 12
    assert body["periodo_tasa"] == "mensual"
    assert as_decimal(body["cuota_fija"]) > Decimal("94500")
    assert as_decimal(body["cuota_fija"]) < Decimal("94600")


def test_periodo_tasa_defaults_to_mensual(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/deudores",
        json={
            "nombre": "Pedro",
            "monto_total": "1000000.00",
            "fecha": "2031-01-01",
            "tasa_interes": "2",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["periodo_tasa"] == "mensual"


def test_reject_tasa_interes_without_numero_cuotas(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/deudores",
        json={
            "nombre": "Pedro",
            "monto_total": "1000000.00",
            "fecha": "2031-01-01",
            "tasa_interes": "2",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_reject_numero_cuotas_without_tasa_interes(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/deudores",
        json={
            "nombre": "Pedro",
            "monto_total": "1000000.00",
            "fecha": "2031-01-01",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_reject_cuota_inicial_without_amortization(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/deudores",
        json={
            "nombre": "Pedro",
            "monto_total": "1000000.00",
            "fecha": "2031-01-01",
            "cuota_inicial": 3,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_reject_cuota_inicial_greater_than_numero_cuotas(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/deudores",
        json={
            "nombre": "Pedro",
            "monto_total": "1000000.00",
            "fecha": "2031-01-01",
            "tasa_interes": "2",
            "numero_cuotas": 12,
            "cuota_inicial": 13,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_amortized_deudor_generates_full_schedule_anchored_to_fecha(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/deudores",
        json={
            "nombre": "Pedro",
            "monto_total": "1000000.00",
            "fecha": "2031-03-01",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 15,
        },
        headers=headers,
    )
    deudor_id = create.json()["id"]

    cuotas = client.get(f"/deudores/{deudor_id}/cuotas", headers=headers).json()
    assert len(cuotas) == 15
    cuotas_sorted = sorted(cuotas, key=lambda c: (c["anio"], c["mes"]))
    assert (cuotas_sorted[0]["anio"], cuotas_sorted[0]["mes"]) == (2031, 3)
    assert (cuotas_sorted[-1]["anio"], cuotas_sorted[-1]["mes"]) == (2032, 5)

    montos = [as_decimal(c["monto_planeado"]) for c in cuotas_sorted]
    # Fixed installment: identical every month except possibly the very last
    # one, which absorbs rounding drift so the schedule's balance hits zero.
    assert len(set(montos[:-1])) == 1
    assert abs(montos[-1] - montos[0]) < Decimal("1.00")

    # Every cuota carries its planned interest component.
    assert all(c["interes"] is not None for c in cuotas_sorted)


def test_non_amortized_deudor_behaves_exactly_as_before(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/deudores",
        json={"nombre": "Pedro", "monto_total": "500000", "fecha": "2031-01-01"},
        headers=headers,
    )
    deudor_id = create.json()["id"]

    body = create.json()
    assert body["tasa_interes"] is None
    assert body["numero_cuotas"] is None
    assert body["cuota_fija"] is None

    cuotas = client.get(f"/deudores/{deudor_id}/cuotas", headers=headers).json()
    assert cuotas == []

    # Abonos still work exactly as before.
    abono = client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "100000", "fecha": "2031-02-01"},
        headers=headers,
    )
    assert abono.status_code == 201


def test_saldo_restante_for_amortized_deudor_reflects_paid_cuotas(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    create = client.post(
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
    )
    deudor_id = create.json()["id"]
    assert as_decimal(create.json()["saldo_restante"]) == Decimal("1000000.00")

    client.patch(
        f"/deudores/{deudor_id}/cuotas/2031/1",
        json={"monto_pagado": "94517.21", "pagado": True},
        headers=headers,
    )

    response = client.get(f"/deudores/{deudor_id}", headers=headers)
    assert as_decimal(response.json()["saldo_restante"]) == Decimal("1000000.00") - Decimal(
        "94517.21"
    )


def test_create_abono_rejected_for_amortized_deudor(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
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
    )
    deudor_id = create.json()["id"]

    response = client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "100000", "fecha": "2031-02-01"},
        headers=headers,
    )
    assert response.status_code == 422
