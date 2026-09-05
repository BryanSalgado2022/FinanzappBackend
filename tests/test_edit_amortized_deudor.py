import datetime

from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def _create_amortized(client: TestClient, headers, numero_cuotas: int = 12):
    today = datetime.date.today()
    response = client.post(
        "/deudores",
        json={
            "nombre": "Pedro",
            "monto_total": "1000000.00",
            "fecha": today.isoformat(),
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": numero_cuotas,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_recalculate_with_no_paid_cuotas_regenerates_from_today(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)

    response = client.put(
        f"/deudores/{deudor['id']}/amortizacion",
        json={
            "monto_total": "2000000.00",
            "tasa_interes": "3",
            "periodo_tasa": "mensual",
            "numero_cuotas": 24,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["numero_cuotas"] == 24
    assert as_decimal(body["monto_total"]) == as_decimal("2000000.00")

    today = datetime.date.today()
    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    assert len(cuotas) == 24
    assert any(c["anio"] == today.year and c["mes"] == today.month for c in cuotas)


def test_recalculate_preserves_paid_cuotas_and_continues_after_them(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)
    today = datetime.date.today()

    # Mark the first cuota paid with a specific amount, so we can confirm it
    # survives the recalculation untouched.
    first_cuota = client.patch(
        f"/deudores/{deudor['id']}/cuotas/{today.year}/{today.month}",
        json={"monto_pagado": "94517.21", "pagado": True},
        headers=headers,
    ).json()

    response = client.put(
        f"/deudores/{deudor['id']}/amortizacion",
        json={
            "monto_total": "1000000.00",
            "tasa_interes": "5",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    paid_cuota = next(c for c in cuotas if c["anio"] == today.year and c["mes"] == today.month)
    assert paid_cuota["monto_pagado"] == first_cuota["monto_pagado"]
    assert paid_cuota["pagado"] is True

    # 11 remaining installments (12 - 1 already paid), starting the month
    # right after the paid one.
    unpaid = [c for c in cuotas if not c["pagado"]]
    assert len(unpaid) == 11
    next_anio, next_mes = (today.year, today.month + 1) if today.month < 12 else (today.year + 1, 1)
    assert any(c["anio"] == next_anio and c["mes"] == next_mes for c in unpaid)


def test_reject_reducing_numero_cuotas_below_paid_count(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers, numero_cuotas=12)
    today = datetime.date.today()

    client.patch(
        f"/deudores/{deudor['id']}/cuotas/{today.year}/{today.month}",
        json={"pagado": True},
        headers=headers,
    )

    response = client.put(
        f"/deudores/{deudor['id']}/amortizacion",
        json={
            "monto_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 0,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_reject_recalculation_on_non_amortized_deudor(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = client.post(
        "/deudores",
        json={"nombre": "SinAmortizar", "monto_total": "500000.00", "fecha": "2031-01-01"},
        headers=headers,
    ).json()

    response = client.put(
        f"/deudores/{deudor['id']}/amortizacion",
        json={
            "monto_total": "500000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_recalculation_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    deudor = _create_amortized(client, headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.put(
        f"/deudores/{deudor['id']}/amortizacion",
        json={
            "monto_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers_b,
    )
    assert response.status_code == 404
