from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_unpaid_entry_past_due_date_is_vencida(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={"nombre": "Internet", "tipo": "gasto_fijo", "dia_vencimiento": 15},
        headers=headers,
    )
    concept_id = create.json()["id"]

    client.put(
        f"/concepts/{concept_id}/entries/2020/1",
        json={"monto_planeado": "100000", "pagado": False},
        headers=headers,
    )

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    entry = next(e for e in entries if e["anio"] == 2020 and e["mes"] == 1)
    assert entry["vencida"] is True


def test_paid_entry_never_vencida(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={"nombre": "Internet", "tipo": "gasto_fijo", "dia_vencimiento": 15},
        headers=headers,
    )
    concept_id = create.json()["id"]

    response = client.put(
        f"/concepts/{concept_id}/entries/2020/1",
        json={"monto_planeado": "100000", "monto_pagado": "100000", "pagado": True},
        headers=headers,
    )
    assert response.json()["vencida"] is False


def test_entry_without_dia_vencimiento_never_vencida(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts", json={"nombre": "Internet", "tipo": "gasto_fijo"}, headers=headers
    )
    concept_id = create.json()["id"]

    response = client.put(
        f"/concepts/{concept_id}/entries/2020/1",
        json={"monto_planeado": "100000", "pagado": False},
        headers=headers,
    )
    assert response.json()["vencida"] is False


def test_entry_not_yet_due_is_not_vencida(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={"nombre": "Internet", "tipo": "gasto_fijo", "dia_vencimiento": 15},
        headers=headers,
    )
    concept_id = create.json()["id"]

    response = client.put(
        f"/concepts/{concept_id}/entries/2099/1",
        json={"monto_planeado": "100000", "pagado": False},
        headers=headers,
    )
    assert response.json()["vencida"] is False
