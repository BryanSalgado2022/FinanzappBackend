import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.entrada_mensual import EntradaMensual
from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def _delete_current_year_entries(session: Session, concepto_id: int, anio: int) -> None:
    entries = session.exec(
        select(EntradaMensual).where(
            EntradaMensual.concepto_id == concepto_id, EntradaMensual.anio == anio
        )
    ).all()
    for entry in entries:
        session.delete(entry)
    session.commit()


def test_lazy_extension_fills_gap_from_prior_year(
    client: TestClient, session: Session, monkeypatch
):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={"nombre": "Sueldo", "tipo": "ingreso", "monto_planeado": "5000000"},
        headers=headers,
    )
    concept_id = create.json()["id"]

    today = datetime.date.today()
    _delete_current_year_entries(session, concept_id, today.year)
    session.add(
        EntradaMensual(
            concepto_id=concept_id, anio=today.year - 1, mes=12, monto_planeado=Decimal("7000000")
        )
    )
    session.commit()

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    current_year_entries = {e["mes"]: e for e in entries if e["anio"] == today.year}
    assert set(current_year_entries.keys()) == set(range(today.month, 13))
    assert as_decimal(current_year_entries[today.month]["monto_planeado"]) == Decimal("7000000")


def test_lazy_extension_never_overwrites_existing_entries(
    client: TestClient, session: Session, monkeypatch
):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={"nombre": "Sueldo", "tipo": "ingreso", "monto_planeado": "5000000"},
        headers=headers,
    )
    concept_id = create.json()["id"]

    today = datetime.date.today()
    _delete_current_year_entries(session, concept_id, today.year)
    session.add(
        EntradaMensual(
            concepto_id=concept_id, anio=today.year - 1, mes=12, monto_planeado=Decimal("7000000")
        )
    )
    # A pre-existing entry for a future month this same year, with a distinct
    # amount - must survive the lazy fill untouched.
    mes_futuro = min(today.month + 1, 12)
    session.add(
        EntradaMensual(
            concepto_id=concept_id,
            anio=today.year,
            mes=mes_futuro,
            monto_planeado=Decimal("9999999"),
        )
    )
    session.commit()

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    preserved = next(e for e in entries if e["anio"] == today.year and e["mes"] == mes_futuro)
    assert as_decimal(preserved["monto_planeado"]) == Decimal("9999999")


def test_no_prior_entry_means_no_generation(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts", json={"nombre": "Sueldo sin monto", "tipo": "ingreso"}, headers=headers
    )
    concept_id = create.json()["id"]

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    assert entries == []


def test_fixed_duration_concept_is_unaffected(client: TestClient, session: Session, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={
            "nombre": "Bono temporal",
            "tipo": "gasto_fijo",
            "monto_planeado": "100000",
            "duracion_meses": 3,
        },
        headers=headers,
    )
    concept_id = create.json()["id"]

    today = datetime.date.today()
    current = next(
        e
        for e in session.exec(
            select(EntradaMensual).where(EntradaMensual.concepto_id == concept_id)
        ).all()
        if e.anio == today.year and e.mes == today.month
    )
    session.delete(current)
    session.commit()

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    assert len(entries) == 2
    assert not any(e["anio"] == today.year and e["mes"] == today.month for e in entries)
