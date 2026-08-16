import datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_create_amortized_debt_saves_terms_and_cuota_fija(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/concepts",
        json={
            "nombre": "Prestamo",
            "tipo": "deuda",
            "valor_total": "1000000.00",
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
        "/concepts",
        json={
            "nombre": "Prestamo",
            "tipo": "deuda",
            "valor_total": "1000000.00",
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
        "/concepts",
        json={"nombre": "Prestamo", "tipo": "deuda", "valor_total": "1000000.00", "tasa_interes": "2"},
        headers=headers,
    )
    assert response.status_code == 422


def test_reject_numero_cuotas_without_tasa_interes(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/concepts",
        json={"nombre": "Prestamo", "tipo": "deuda", "valor_total": "1000000.00", "numero_cuotas": 12},
        headers=headers,
    )
    assert response.status_code == 422


def test_reject_amortization_fields_on_non_debt(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/concepts",
        json={
            "nombre": "Sueldo",
            "tipo": "ingreso",
            "tasa_interes": "2",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_amortized_debt_generates_full_schedule_spanning_years(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={
            "nombre": "Prestamo largo",
            "tipo": "deuda",
            "valor_total": "1000000.00",
            "tasa_interes": "2",
            "periodo_tasa": "mensual",
            "numero_cuotas": 15,
        },
        headers=headers,
    )
    concept_id = create.json()["id"]

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    assert len(entries) == 15

    today = datetime.date.today()
    years = {e["anio"] for e in entries}
    assert len(years) >= 2
    assert min(years) == today.year

    entries_sorted = sorted(entries, key=lambda e: (e["anio"], e["mes"]))
    montos = [as_decimal(e["monto_planeado"]) for e in entries_sorted]
    # Fixed installment: identical every month except possibly the very last
    # one, which absorbs rounding drift so the schedule's balance hits zero.
    assert len(set(montos[:-1])) == 1
    assert abs(montos[-1] - montos[0]) < Decimal("1.00")


def test_reject_update_valor_total_on_amortized_debt(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={
            "nombre": "Prestamo",
            "tipo": "deuda",
            "valor_total": "1000000.00",
            "tasa_interes": "2",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    concept_id = create.json()["id"]

    response = client.patch(
        f"/concepts/{concept_id}", json={"valor_total": "2000000.00"}, headers=headers
    )
    assert response.status_code == 422


def test_update_valor_total_still_works_on_non_amortized_debt(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={"nombre": "Prestamo simple", "tipo": "deuda", "valor_total": "1000000.00"},
        headers=headers,
    )
    concept_id = create.json()["id"]

    response = client.patch(
        f"/concepts/{concept_id}", json={"valor_total": "2000000.00"}, headers=headers
    )
    assert response.status_code == 200
    assert as_decimal(response.json()["valor_total"]) == Decimal("2000000.00")
