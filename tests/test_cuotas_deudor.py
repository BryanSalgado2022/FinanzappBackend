import datetime

from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def _create_amortized(client: TestClient, headers, numero_cuotas: int = 12):
    response = client.post(
        "/deudores",
        json={
            "nombre": "Pedro",
            "monto_total": "1000000.00",
            "fecha": "2031-01-01",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": numero_cuotas,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_listing_a_deudors_scheduled_cuotas(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)

    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    assert len(cuotas) == 12


def test_marking_a_cuota_paid_records_amount_and_date(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)

    response = client.patch(
        f"/deudores/{deudor['id']}/cuotas/2031/1",
        json={"monto_pagado": "94517.21", "pagado": True},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert as_decimal(body["monto_pagado"]) == as_decimal("94517.21")
    assert body["pagado"] is True
    assert body["fecha_pago"] == datetime.date.today().isoformat()


def test_marking_a_cuota_paid_without_amount_defaults_to_planned(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)

    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    planeado = next(c for c in cuotas if c["anio"] == 2031 and c["mes"] == 1)["monto_planeado"]

    response = client.patch(
        f"/deudores/{deudor['id']}/cuotas/2031/1", json={"pagado": True}, headers=headers
    )
    assert response.json()["monto_pagado"] == planeado


def test_marking_a_cuota_unpaid_clears_its_payment_date(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)

    client.patch(
        f"/deudores/{deudor['id']}/cuotas/2031/1",
        json={"monto_pagado": "94517.21", "pagado": True},
        headers=headers,
    )
    response = client.patch(
        f"/deudores/{deudor['id']}/cuotas/2031/1", json={"pagado": False}, headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["fecha_pago"] is None
    assert response.json()["pagado"] is False


def test_listing_cuotas_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    deudor = _create_amortized(client, headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers_b)
    assert response.status_code == 404


def test_marking_cuota_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    deudor = _create_amortized(client, headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.patch(
        f"/deudores/{deudor['id']}/cuotas/2031/1", json={"pagado": True}, headers=headers_b
    )
    assert response.status_code == 404
