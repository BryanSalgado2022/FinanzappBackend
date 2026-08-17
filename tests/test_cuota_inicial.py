import datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def _crear_deuda(client: TestClient, headers, **overrides):
    payload = {
        "nombre": "Prestamo",
        "tipo": "deuda",
        "valor_total": "1000000.00",
        "tasa_interes": "2",
        "periodo_tasa": "mensual",
        "numero_cuotas": 12,
    }
    payload.update(overrides)
    return client.post("/concepts", json=payload, headers=headers)


def test_cuota_inicial_generates_only_remaining_installments(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = _crear_deuda(client, headers, cuota_inicial=5)
    assert create.status_code == 201, create.text
    concept_id = create.json()["id"]

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    assert len(entries) == 12 - 5 + 1

    today = datetime.date.today()
    entries_sorted = sorted(entries, key=lambda e: (e["anio"], e["mes"]))
    assert (entries_sorted[0]["anio"], entries_sorted[0]["mes"]) == (today.year, today.month)


def test_cuota_inicial_defaults_to_full_schedule(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = _crear_deuda(client, headers)
    assert create.status_code == 201, create.text
    concept_id = create.json()["id"]

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    assert len(entries) == 12
    assert create.json()["cuota_inicial"] is None


def test_saldo_restante_reflects_cuota_inicial(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)

    completo = _crear_deuda(client, headers, nombre="Completo")
    parcial = _crear_deuda(client, headers, nombre="Parcial", cuota_inicial=5)

    saldo_completo = as_decimal(completo.json()["saldo_restante"])
    saldo_parcial = as_decimal(parcial.json()["saldo_restante"])

    assert saldo_parcial < saldo_completo
    assert saldo_parcial > Decimal("0")


def test_reject_cuota_inicial_without_amortizacion(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/concepts",
        json={"nombre": "Prestamo", "tipo": "deuda", "valor_total": "1000000.00", "cuota_inicial": 2},
        headers=headers,
    )
    assert response.status_code == 422


def test_reject_cuota_inicial_out_of_range(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = _crear_deuda(client, headers, cuota_inicial=13)
    assert response.status_code == 422


def test_reject_editing_cuota_inicial(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = _crear_deuda(client, headers)
    concept_id = create.json()["id"]

    response = client.patch(f"/concepts/{concept_id}", json={"cuota_inicial": 3}, headers=headers)
    assert response.status_code == 422
    assert "cuota_inicial" in response.json()["detail"]
