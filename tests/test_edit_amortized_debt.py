import datetime

from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def _create_amortized(client: TestClient, headers, numero_cuotas: int = 12):
    response = client.post(
        "/concepts",
        json={
            "nombre": "Prestamo",
            "tipo": "deuda",
            "valor_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": numero_cuotas,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_recalculate_with_no_paid_entries_regenerates_from_today(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized(client, headers)

    response = client.put(
        f"/concepts/{concept['id']}/amortizacion",
        json={
            "valor_total": "2000000.00",
            "tasa_interes": "3",
            "periodo_tasa": "mensual",
            "numero_cuotas": 24,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["numero_cuotas"] == 24
    assert as_decimal(body["valor_total"]) == as_decimal("2000000.00")

    today = datetime.date.today()
    entries = client.get(f"/concepts/{concept['id']}/entries", headers=headers).json()
    assert len(entries) == 24
    assert any(e["anio"] == today.year and e["mes"] == today.month for e in entries)


def test_recalculate_preserves_paid_entries_and_continues_after_them(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized(client, headers)
    today = datetime.date.today()

    # Mark the first entry paid with a specific amount, so we can confirm it
    # survives the recalculation untouched.
    first_entry = client.put(
        f"/concepts/{concept['id']}/entries/{today.year}/{today.month}",
        json={"monto_planeado": "94517.21", "monto_pagado": "94517.21", "pagado": True},
        headers=headers,
    ).json()

    response = client.put(
        f"/concepts/{concept['id']}/amortizacion",
        json={
            "valor_total": "1000000.00",
            "tasa_interes": "5",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    entries = client.get(f"/concepts/{concept['id']}/entries", headers=headers).json()
    paid_entry = next(e for e in entries if e["anio"] == today.year and e["mes"] == today.month)
    assert paid_entry["monto_pagado"] == first_entry["monto_pagado"]
    assert paid_entry["pagado"] is True

    # 11 remaining installments (12 - 1 already paid), starting the month
    # right after the paid one.
    unpaid = [e for e in entries if not e["pagado"]]
    assert len(unpaid) == 11
    next_anio, next_mes = (today.year, today.month + 1) if today.month < 12 else (today.year + 1, 1)
    assert any(e["anio"] == next_anio and e["mes"] == next_mes for e in unpaid)


def test_reject_reducing_numero_cuotas_below_paid_count(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized(client, headers, numero_cuotas=12)
    today = datetime.date.today()

    client.put(
        f"/concepts/{concept['id']}/entries/{today.year}/{today.month}",
        json={"monto_planeado": "94517.21", "pagado": True},
        headers=headers,
    )

    response = client.put(
        f"/concepts/{concept['id']}/amortizacion",
        json={
            "valor_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 0,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_reject_recalculation_on_non_amortized_debt(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = client.post(
        "/concepts",
        json={"nombre": "SinAmortizar", "tipo": "deuda", "valor_total": "500000.00"},
        headers=headers,
    ).json()

    response = client.put(
        f"/concepts/{concept['id']}/amortizacion",
        json={
            "valor_total": "500000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_reject_recalculation_on_non_deuda_concept(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = client.post(
        "/concepts", json={"nombre": "Sueldo", "tipo": "ingreso"}, headers=headers
    ).json()

    response = client.put(
        f"/concepts/{concept['id']}/amortizacion",
        json={
            "valor_total": "500000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_recalculation_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    concept = _create_amortized(client, headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.put(
        f"/concepts/{concept['id']}/amortizacion",
        json={
            "valor_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers_b,
    )
    assert response.status_code == 404
