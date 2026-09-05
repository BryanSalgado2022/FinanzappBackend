import datetime

from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


# --- Concepto (deuda) ---


def _create_plain_debt(client: TestClient, headers, valor_total: str = "500000.00") -> dict:
    response = client.post(
        "/concepts",
        json={"nombre": "SinAmortizar", "tipo": "deuda", "valor_total": valor_total},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_activate_amortization_on_concept_generates_schedule(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = _create_plain_debt(client, headers)

    response = client.post(
        f"/concepts/{concept['id']}/amortizacion",
        json={
            "valor_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["numero_cuotas"] == 12
    assert as_decimal(body["cuota_fija"]) > as_decimal("94500")

    today = datetime.date.today()
    entries = client.get(f"/concepts/{concept['id']}/entries", headers=headers).json()
    assert len(entries) == 12
    assert any(e["anio"] == today.year and e["mes"] == today.month for e in entries)


def test_activate_amortization_preserves_paid_entries_and_replaces_unpaid(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    concept = _create_plain_debt(client, headers)
    concept_id = concept["id"]
    today = datetime.date.today()

    # Existing (non-schedule) entries from before activation.
    client.put(
        f"/concepts/{concept_id}/entries/{today.year}/{today.month}",
        json={"monto_planeado": "50000.00", "monto_pagado": "50000.00", "pagado": True},
        headers=headers,
    )
    next_anio, next_mes = (today.year, today.month + 1) if today.month < 12 else (today.year + 1, 1)
    client.put(
        f"/concepts/{concept_id}/entries/{next_anio}/{next_mes}",
        json={"monto_planeado": "50000.00", "pagado": False},
        headers=headers,
    )

    response = client.post(
        f"/concepts/{concept_id}/amortizacion",
        json={
            "valor_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    paid_entry = next(e for e in entries if e["anio"] == today.year and e["mes"] == today.month)
    assert paid_entry["monto_pagado"] == "50000.00"
    assert paid_entry["pagado"] is True

    stale_unpaid = [e for e in entries if e["anio"] == next_anio and e["mes"] == next_mes]
    assert len(stale_unpaid) == 1
    assert stale_unpaid[0]["monto_planeado"] != "50000.00"


def test_activate_amortization_respects_cuota_inicial(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = _create_plain_debt(client, headers)

    response = client.post(
        f"/concepts/{concept['id']}/amortizacion",
        json={
            "valor_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
            "cuota_inicial": 5,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    entries = client.get(f"/concepts/{concept['id']}/entries", headers=headers).json()
    assert len(entries) == 8  # cuotas 5..12


def test_reject_activation_on_already_amortized_concept(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={
            "nombre": "YaAmortizada",
            "tipo": "deuda",
            "valor_total": "1000000.00",
            "tasa_interes": "2",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    concept = create.json()

    response = client.post(
        f"/concepts/{concept['id']}/amortizacion",
        json={
            "valor_total": "1000000.00",
            "tasa_interes": "3",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_reject_activation_on_non_deuda_concept(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = client.post(
        "/concepts", json={"nombre": "Sueldo", "tipo": "ingreso"}, headers=headers
    ).json()

    response = client.post(
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


def test_activation_scoped_to_owner_concept(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    concept = _create_plain_debt(client, headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.post(
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


# --- Deudor ---


def _create_plain_deudor(client: TestClient, headers, monto_total: str = "500000") -> dict:
    response = client.post(
        "/deudores",
        json={"nombre": "SinAmortizar", "monto_total": monto_total, "fecha": "2031-01-01"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_activate_amortization_on_deudor_generates_schedule(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_plain_deudor(client, headers)

    response = client.post(
        f"/deudores/{deudor['id']}/amortizacion",
        json={
            "monto_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["numero_cuotas"] == 12

    today = datetime.date.today()
    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    assert len(cuotas) == 12
    assert any(c["anio"] == today.year and c["mes"] == today.month for c in cuotas)


def test_activate_amortization_preserves_existing_abonos_as_history(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    deudor = _create_plain_deudor(client, headers)
    deudor_id = deudor["id"]

    client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "100000", "fecha": "2031-02-01"},
        headers=headers,
    )

    response = client.post(
        f"/deudores/{deudor_id}/amortizacion",
        json={
            "monto_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert as_decimal(response.json()["saldo_restante"]) == as_decimal("1000000.00")

    abonos = client.get(f"/deudores/{deudor_id}/abonos", headers=headers).json()
    assert len(abonos) == 1
    assert abonos[0]["monto"] == "100000.00"


def test_activate_amortization_respects_cuota_inicial_deudor(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_plain_deudor(client, headers)

    response = client.post(
        f"/deudores/{deudor['id']}/amortizacion",
        json={
            "monto_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
            "cuota_inicial": 5,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    assert len(cuotas) == 8  # cuotas 5..12


def test_reject_activation_on_already_amortized_deudor(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/deudores",
        json={
            "nombre": "YaAmortizado",
            "monto_total": "1000000.00",
            "fecha": "2031-01-01",
            "tasa_interes": "2",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    deudor = create.json()

    response = client.post(
        f"/deudores/{deudor['id']}/amortizacion",
        json={
            "monto_total": "1000000.00",
            "tasa_interes": "3",
            "periodo_tasa": "mensual",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_activation_scoped_to_owner_deudor(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    deudor = _create_plain_deudor(client, headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.post(
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
