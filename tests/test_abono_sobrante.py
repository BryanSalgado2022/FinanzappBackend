import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.entrada_mensual import EntradaMensual
from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def _create_amortized_deudor(client: TestClient, headers, numero_cuotas: int = 12):
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


def _create_amortized_concepto(client: TestClient, headers, numero_cuotas: int = 12):
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


# ---------------------------------------------------------------------------
# Concepto: the underlying principal-prepayment mechanism (new)
# ---------------------------------------------------------------------------


def test_concepto_reducir_cuota_keeps_installment_count_and_lowers_cuota(
    client: TestClient, monkeypatch, session: Session
):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized_concepto(client, headers)

    from app.services import concept_service

    concept_service.registrar_abono_capital(
        session, 1, concept["id"], monto=Decimal("100000.00"), fecha=datetime.date.today(), modo="reducir_cuota"
    )

    response = client.get(f"/concepts/{concept['id']}", headers=headers)
    body = response.json()
    assert body["numero_cuotas"] == 12
    assert as_decimal(body["valor_total"]) == as_decimal("1000000.00")
    assert as_decimal(body["saldo_restante"]) == as_decimal("900000.00")
    assert as_decimal(body["cuota_fija"]) == as_decimal("85103.64")


def test_concepto_reducir_plazo_keeps_cuota_and_shortens_schedule(
    client: TestClient, monkeypatch, session: Session
):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized_concepto(client, headers)

    from app.services import concept_service

    concept_service.registrar_abono_capital(
        session, 1, concept["id"], monto=Decimal("100000.00"), fecha=datetime.date.today(), modo="reducir_plazo"
    )

    response = client.get(f"/concepts/{concept['id']}", headers=headers)
    body = response.json()
    assert body["numero_cuotas"] == 11
    assert as_decimal(body["saldo_restante"]) == as_decimal("900000.00")
    assert as_decimal(body["cuota_fija"]) == as_decimal("91960.15")


def test_concepto_already_paid_entries_untouched_by_prepayment(
    client: TestClient, monkeypatch, session: Session
):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized_concepto(client, headers)
    today = datetime.date.today()

    first_entry = client.put(
        f"/concepts/{concept['id']}/entries/{today.year}/{today.month}",
        json={"monto_planeado": "94559.60", "monto_pagado": "94559.60", "pagado": True},
        headers=headers,
    ).json()

    from app.services import concept_service

    concept_service.registrar_abono_capital(
        session, 1, concept["id"], monto=Decimal("50000.00"), fecha=today, modo="reducir_cuota"
    )

    entries = client.get(f"/concepts/{concept['id']}/entries", headers=headers).json()
    paid_entry = next(e for e in entries if e["anio"] == today.year and e["mes"] == today.month)
    assert paid_entry["monto_pagado"] == first_entry["monto_pagado"]
    assert paid_entry["pagado"] is True
    assert len([e for e in entries if not e["pagado"]]) == 11


def test_concepto_full_prepayment_finalizes(client: TestClient, monkeypatch, session: Session):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized_concepto(client, headers)
    today = datetime.date.today()

    from app.services import concept_service

    concept_service.registrar_abono_capital(
        session, 1, concept["id"], monto=Decimal("1000000.00"), fecha=today, modo="reducir_cuota"
    )

    response = client.get(f"/concepts/{concept['id']}", headers=headers)
    body = response.json()
    assert body["activo"] is False
    assert body["finalizado_en"] == today.isoformat()
    assert as_decimal(body["saldo_restante"]) == as_decimal("0")

    entries = client.get(f"/concepts/{concept['id']}/entries", headers=headers).json()
    assert entries == []


def test_concepto_prepayment_rejected_on_non_amortized(client: TestClient, monkeypatch, session: Session):
    headers = _headers(client, monkeypatch)
    concept = client.post(
        "/concepts",
        json={"nombre": "SinAmortizar", "tipo": "deuda", "valor_total": "500000.00"},
        headers=headers,
    ).json()

    from app.services import concept_service

    with pytest.raises(ValueError):
        concept_service.registrar_abono_capital(
            session, 1, concept["id"], monto=Decimal("100000.00"), fecha=datetime.date.today(), modo="reducir_cuota"
        )


def test_concepto_reducir_plazo_rejected_when_cuota_does_not_cover_interest(
    client: TestClient, monkeypatch, session: Session
):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized_concepto(client, headers)

    entry = session.exec(
        select(EntradaMensual).where(EntradaMensual.concepto_id == concept["id"])
    ).first()
    entry.monto_planeado = Decimal("1.00")
    session.add(entry)
    session.commit()

    from app.services import concept_service

    with pytest.raises(ValueError):
        concept_service.registrar_abono_capital(
            session, 1, concept["id"], monto=Decimal("1000.00"), fecha=datetime.date.today(), modo="reducir_plazo"
        )


def test_concepto_prepayment_scoped_to_owner(client: TestClient, monkeypatch, session: Session):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    concept = _create_amortized_concepto(client, headers_a)

    auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")

    from app.services import concept_service
    from app.services.concept_service import ConceptoNotFoundError

    with pytest.raises(ConceptoNotFoundError):
        concept_service.registrar_abono_capital(
            session, 2, concept["id"], monto=Decimal("100000.00"), fecha=datetime.date.today(), modo="reducir_cuota"
        )


# ---------------------------------------------------------------------------
# Deudor: routing a payment surplus into a principal prepayment
# ---------------------------------------------------------------------------


def test_deudor_surplus_reducir_plazo(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized_deudor(client, headers)
    today = datetime.date.today()

    response = client.patch(
        f"/deudores/{deudor['id']}/cuotas/{today.year}/{today.month}",
        json={"monto_pagado": "200000.00", "pagado": True, "abono_capital_modo": "reducir_plazo"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    cuota = response.json()
    assert as_decimal(cuota["monto_pagado"]) == as_decimal("94559.60")

    deudor_after = client.get(f"/deudores/{deudor['id']}", headers=headers).json()
    assert deudor_after["numero_cuotas"] == 11
    assert as_decimal(deudor_after["saldo_restante"]) == as_decimal("800000.00")

    abonos = client.get(f"/deudores/{deudor['id']}/abonos", headers=headers).json()
    assert len(abonos) == 1
    assert abonos[0]["es_abono_capital"] is True
    assert as_decimal(abonos[0]["monto"]) == as_decimal("105440.40")


def test_deudor_surplus_reducir_cuota(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized_deudor(client, headers)
    today = datetime.date.today()

    response = client.patch(
        f"/deudores/{deudor['id']}/cuotas/{today.year}/{today.month}",
        json={"monto_pagado": "150000.00", "pagado": True, "abono_capital_modo": "reducir_cuota"},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    deudor_after = client.get(f"/deudores/{deudor['id']}", headers=headers).json()
    assert deudor_after["numero_cuotas"] == 12
    assert as_decimal(deudor_after["saldo_restante"]) == as_decimal("850000.00")


def test_deudor_mark_paid_without_modo_is_unchanged(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized_deudor(client, headers)
    today = datetime.date.today()

    response = client.patch(
        f"/deudores/{deudor['id']}/cuotas/{today.year}/{today.month}",
        json={"monto_pagado": "200000.00", "pagado": True},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    cuota = response.json()
    assert as_decimal(cuota["monto_pagado"]) == as_decimal("200000.00")

    abonos = client.get(f"/deudores/{deudor['id']}/abonos", headers=headers).json()
    assert abonos == []

    deudor_after = client.get(f"/deudores/{deudor['id']}", headers=headers).json()
    assert deudor_after["numero_cuotas"] == 12
    assert as_decimal(deudor_after["saldo_restante"]) == as_decimal("800000.00")


def test_deudor_surplus_rejected_when_no_surplus(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor = _create_amortized_deudor(client, headers)
    today = datetime.date.today()

    response = client.patch(
        f"/deudores/{deudor['id']}/cuotas/{today.year}/{today.month}",
        json={"monto_pagado": "94559.60", "pagado": True, "abono_capital_modo": "reducir_cuota"},
        headers=headers,
    )
    assert response.status_code == 422


def test_deudor_surplus_rejected_on_non_amortized(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    today = datetime.date.today()
    deudor = client.post(
        "/deudores",
        json={"nombre": "SinAmortizar", "monto_total": "500000.00", "fecha": today.isoformat()},
        headers=headers,
    ).json()

    response = client.patch(
        f"/deudores/{deudor['id']}/cuotas/{today.year}/{today.month}",
        json={"monto_pagado": "600000.00", "pagado": True, "abono_capital_modo": "reducir_cuota"},
        headers=headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Concepto: routing a payment surplus into a principal prepayment
# ---------------------------------------------------------------------------


def test_concepto_surplus_reducir_plazo(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized_concepto(client, headers)
    today = datetime.date.today()

    response = client.put(
        f"/concepts/{concept['id']}/entries/{today.year}/{today.month}",
        json={
            "monto_planeado": "94559.60",
            "monto_pagado": "200000.00",
            "pagado": True,
            "abono_capital_modo": "reducir_plazo",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    entry = response.json()
    assert as_decimal(entry["monto_pagado"]) == as_decimal("94559.60")

    concept_after = client.get(f"/concepts/{concept['id']}", headers=headers).json()
    assert concept_after["numero_cuotas"] == 11
    assert as_decimal(concept_after["saldo_restante"]) == as_decimal("800000.00")


def test_concepto_surplus_reducir_cuota(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized_concepto(client, headers)
    today = datetime.date.today()

    response = client.put(
        f"/concepts/{concept['id']}/entries/{today.year}/{today.month}",
        json={
            "monto_planeado": "94559.60",
            "monto_pagado": "150000.00",
            "pagado": True,
            "abono_capital_modo": "reducir_cuota",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    concept_after = client.get(f"/concepts/{concept['id']}", headers=headers).json()
    assert concept_after["numero_cuotas"] == 12
    assert as_decimal(concept_after["saldo_restante"]) == as_decimal("850000.00")


def test_concepto_mark_paid_without_modo_is_unchanged(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized_concepto(client, headers)
    today = datetime.date.today()

    response = client.put(
        f"/concepts/{concept['id']}/entries/{today.year}/{today.month}",
        json={"monto_planeado": "94559.60", "monto_pagado": "200000.00", "pagado": True},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    entry = response.json()
    assert as_decimal(entry["monto_pagado"]) == as_decimal("200000.00")

    concept_after = client.get(f"/concepts/{concept['id']}", headers=headers).json()
    assert concept_after["numero_cuotas"] == 12
    assert as_decimal(concept_after["saldo_restante"]) == as_decimal("800000.00")


def test_concepto_surplus_rejected_when_no_surplus(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = _create_amortized_concepto(client, headers)
    today = datetime.date.today()

    response = client.put(
        f"/concepts/{concept['id']}/entries/{today.year}/{today.month}",
        json={
            "monto_planeado": "94559.60",
            "monto_pagado": "94559.60",
            "pagado": True,
            "abono_capital_modo": "reducir_cuota",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_concepto_surplus_rejected_on_non_amortized(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    today = datetime.date.today()
    concept = client.post(
        "/concepts",
        json={"nombre": "SinAmortizar", "tipo": "deuda", "valor_total": "500000.00"},
        headers=headers,
    ).json()

    response = client.put(
        f"/concepts/{concept['id']}/entries/{today.year}/{today.month}",
        json={
            "monto_planeado": "500000.00",
            "monto_pagado": "600000.00",
            "pagado": True,
            "abono_capital_modo": "reducir_cuota",
        },
        headers=headers,
    )
    assert response.status_code == 422
