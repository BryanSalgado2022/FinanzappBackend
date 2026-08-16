import datetime

from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_recurring_income_without_duration_fills_rest_of_year(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={"nombre": "Sueldo", "tipo": "ingreso", "monto_planeado": "7000000"},
        headers=headers,
    )
    concept_id = create.json()["id"]

    today = datetime.date.today()
    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    meses_generados = {e["mes"] for e in entries if e["anio"] == today.year}
    assert meses_generados == set(range(today.month, 13))


def test_reject_duracion_meses_on_deuda(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/concepts",
        json={"nombre": "Deuda", "tipo": "deuda", "valor_total": "1000000", "duracion_meses": 6},
        headers=headers,
    )
    assert response.status_code == 422


def test_fixed_duration_generates_exact_window(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={
            "nombre": "Ingreso temporal",
            "tipo": "ingreso",
            "monto_planeado": "1000000",
            "duracion_meses": 15,
        },
        headers=headers,
    )
    concept_id = create.json()["id"]

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    assert len(entries) == 15

    today = datetime.date.today()
    years = {e["anio"] for e in entries}
    assert min(years) == today.year
    assert len(years) >= 2  # 15 months from "today" always crosses into a new year

    for e in entries:
        assert as_decimal(e["monto_planeado"]) == as_decimal("1000000")


def test_fixed_duration_does_not_extend_beyond_window_on_edit(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={
            "nombre": "Gasto temporal",
            "tipo": "gasto_fijo",
            "monto_planeado": "50000",
            "duracion_meses": 3,
        },
        headers=headers,
    )
    concept_id = create.json()["id"]

    today = datetime.date.today()
    # Editing the current month's entry must not generate entries beyond the
    # original 3-month window, even though the old open-ended fill-forward
    # would otherwise extend through December.
    client.put(
        f"/concepts/{concept_id}/entries/{today.year}/{today.month}",
        json={"monto_planeado": "60000"},
        headers=headers,
    )

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    assert len(entries) == 3
