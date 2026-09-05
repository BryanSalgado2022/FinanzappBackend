import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.deudor import CuotaDeudor
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


def test_reducir_cuota_keeps_installment_count_and_lowers_cuota(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)
    today = datetime.date.today()

    response = client.post(
        f"/deudores/{deudor['id']}/abono-capital",
        json={"monto": "100000.00", "fecha": today.isoformat(), "modo": "reducir_cuota"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["numero_cuotas"] == 12
    assert as_decimal(body["monto_total"]) == as_decimal("1000000.00")
    assert as_decimal(body["saldo_restante"]) == as_decimal("900000.00")
    assert as_decimal(body["cuota_fija"]) == as_decimal("85103.64")

    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    assert len(cuotas) == 12
    assert all(not c["pagado"] for c in cuotas)

    abonos = client.get(f"/deudores/{deudor['id']}/abonos", headers=headers).json()
    assert len(abonos) == 1
    assert abonos[0]["es_abono_capital"] is True


def test_reducir_plazo_keeps_cuota_and_shortens_schedule(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)
    today = datetime.date.today()

    response = client.post(
        f"/deudores/{deudor['id']}/abono-capital",
        json={"monto": "100000.00", "fecha": today.isoformat(), "modo": "reducir_plazo"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["numero_cuotas"] == 11
    assert as_decimal(body["monto_total"]) == as_decimal("1000000.00")
    assert as_decimal(body["saldo_restante"]) == as_decimal("900000.00")
    assert as_decimal(body["cuota_fija"]) == as_decimal("91960.15")

    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    assert len(cuotas) == 11
    assert all(not c["pagado"] for c in cuotas)


def test_paid_installments_untouched_by_abono_capital(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)
    today = datetime.date.today()

    first_cuota = client.patch(
        f"/deudores/{deudor['id']}/cuotas/{today.year}/{today.month}",
        json={"monto_pagado": "94559.60", "pagado": True},
        headers=headers,
    ).json()

    response = client.post(
        f"/deudores/{deudor['id']}/abono-capital",
        json={"monto": "50000.00", "fecha": today.isoformat(), "modo": "reducir_cuota"},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    paid_cuota = next(c for c in cuotas if c["anio"] == today.year and c["mes"] == today.month)
    assert paid_cuota["monto_pagado"] == first_cuota["monto_pagado"]
    assert paid_cuota["pagado"] is True

    unpaid = [c for c in cuotas if not c["pagado"]]
    assert len(unpaid) == 11
    next_anio, next_mes = (today.year, today.month + 1) if today.month < 12 else (today.year + 1, 1)
    assert any(c["anio"] == next_anio and c["mes"] == next_mes for c in unpaid)


def test_full_prepayment_finalizes_debtor(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)
    today = datetime.date.today()

    response = client.post(
        f"/deudores/{deudor['id']}/abono-capital",
        json={"monto": "1000000.00", "fecha": today.isoformat(), "modo": "reducir_cuota"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["activo"] is False
    assert body["finalizado_en"] == today.isoformat()
    assert as_decimal(body["saldo_restante"]) == as_decimal("0")

    cuotas = client.get(f"/deudores/{deudor['id']}/cuotas", headers=headers).json()
    assert cuotas == []


def test_reject_abono_capital_on_non_amortized_debtor(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = client.post(
        "/deudores",
        json={"nombre": "SinAmortizar", "monto_total": "500000.00", "fecha": "2031-01-01"},
        headers=headers,
    ).json()

    response = client.post(
        f"/deudores/{deudor['id']}/abono-capital",
        json={"monto": "100000.00", "fecha": "2031-02-01", "modo": "reducir_cuota"},
        headers=headers,
    )
    assert response.status_code == 422


def test_reducir_plazo_rejected_when_cuota_does_not_cover_interest(
    client: TestClient, monkeypatch, session: Session
):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)
    today = datetime.date.today()

    # A validly generated schedule's fixed cuota always covers its own
    # period's interest, so the only way to exercise this rejection is to
    # force an artificially tiny installment directly in the DB.
    cuota = session.exec(
        select(CuotaDeudor).where(CuotaDeudor.deudor_id == deudor["id"])
    ).first()
    cuota.monto_planeado = Decimal("1.00")
    session.add(cuota)
    session.commit()

    response = client.post(
        f"/deudores/{deudor['id']}/abono-capital",
        json={"monto": "1000.00", "fecha": today.isoformat(), "modo": "reducir_plazo"},
        headers=headers,
    )
    assert response.status_code == 422


def test_monto_total_unchanged_by_prepayment(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized(client, headers)
    today = datetime.date.today()

    for modo in ("reducir_cuota", "reducir_plazo"):
        response = client.post(
            f"/deudores/{deudor['id']}/abono-capital",
            json={"monto": "50000.00", "fecha": today.isoformat(), "modo": modo},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert as_decimal(response.json()["monto_total"]) == as_decimal("1000000.00")


def test_abono_capital_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    deudor = _create_amortized(client, headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.post(
        f"/deudores/{deudor['id']}/abono-capital",
        json={"monto": "100000.00", "fecha": "2031-02-01", "modo": "reducir_cuota"},
        headers=headers_b,
    )
    assert response.status_code == 404
