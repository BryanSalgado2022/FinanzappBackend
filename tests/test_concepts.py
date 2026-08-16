from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import as_decimal, auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_create_each_concept_type(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    for tipo in ("deuda", "gasto_fijo", "ingreso"):
        response = client.post("/concepts", json={"nombre": tipo, "tipo": tipo}, headers=headers)
        assert response.status_code == 201, response.text
        assert response.json()["tipo"] == tipo


def test_reject_invalid_tipo(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/concepts", json={"nombre": "X", "tipo": "not-a-type"}, headers=headers
    )
    assert response.status_code == 422


def test_reject_valor_total_on_non_debt(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/concepts",
        json={"nombre": "Internet", "tipo": "gasto_fijo", "valor_total": "100.00"},
        headers=headers,
    )
    assert response.status_code == 422


def test_remaining_balance_across_years(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={"nombre": "Prestamo", "tipo": "deuda", "valor_total": "1000.00"},
        headers=headers,
    )
    concept_id = create.json()["id"]

    client.put(
        f"/concepts/{concept_id}/entries/2024/6",
        json={"monto_planeado": "300.00", "monto_pagado": "300.00", "pagado": True},
        headers=headers,
    )
    client.put(
        f"/concepts/{concept_id}/entries/2025/6",
        json={"monto_planeado": "300.00", "monto_pagado": "300.00", "pagado": True},
        headers=headers,
    )

    response = client.get(f"/concepts/{concept_id}", headers=headers)
    assert as_decimal(response.json()["saldo_restante"]) == Decimal("400.00")


def test_remaining_balance_zero_when_fully_paid(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={"nombre": "Prestamo chico", "tipo": "deuda", "valor_total": "500.00"},
        headers=headers,
    )
    concept_id = create.json()["id"]

    client.put(
        f"/concepts/{concept_id}/entries/2024/1",
        json={"monto_planeado": "500.00", "monto_pagado": "500.00", "pagado": True},
        headers=headers,
    )

    response = client.get(f"/concepts/{concept_id}", headers=headers)
    assert as_decimal(response.json()["saldo_restante"]) == Decimal("0")


def test_remaining_balance_drops_when_marked_paid_without_amount(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={"nombre": "Prestamo", "tipo": "deuda", "valor_total": "1000.00"},
        headers=headers,
    )
    concept_id = create.json()["id"]

    client.put(
        f"/concepts/{concept_id}/entries/2024/1",
        json={"monto_planeado": "300.00", "pagado": True},
        headers=headers,
    )

    response = client.get(f"/concepts/{concept_id}", headers=headers)
    assert as_decimal(response.json()["saldo_restante"]) == Decimal("700.00")


def test_list_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    client.post("/concepts", json={"nombre": "A1", "tipo": "ingreso"}, headers=headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    client.post("/concepts", json={"nombre": "B1", "tipo": "ingreso"}, headers=headers_b)

    response = client.get("/concepts", headers=headers_a)
    nombres = [c["nombre"] for c in response.json()]
    assert nombres == ["A1"]


def test_delete_concept(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post("/concepts", json={"nombre": "Temporal", "tipo": "ingreso"}, headers=headers)
    concept_id = create.json()["id"]

    delete = client.delete(f"/concepts/{concept_id}", headers=headers)
    assert delete.status_code == 204

    get = client.get(f"/concepts/{concept_id}", headers=headers)
    assert get.status_code == 404


def test_delete_concept_with_monthly_entries(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts", json={"nombre": "Con entradas", "tipo": "gasto_fijo"}, headers=headers
    )
    concept_id = create.json()["id"]
    client.put(
        f"/concepts/{concept_id}/entries/2030/1",
        json={"monto_planeado": "1000.00"},
        headers=headers,
    )

    delete = client.delete(f"/concepts/{concept_id}", headers=headers)
    assert delete.status_code == 204
