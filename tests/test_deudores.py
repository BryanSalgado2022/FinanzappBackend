from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_create_deudor_with_required_fields_only(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/deudores",
        json={"nombre": "Juan", "monto_total": "500000", "fecha": "2026-01-01"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["nombre"] == "Juan"
    assert body["monto_total"] == "500000.00"
    assert body["garantia"] is None
    assert body["activo"] is True
    assert body["saldo_restante"] == "500000.00"


def test_create_deudor_with_garantia(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/deudores",
        json={
            "nombre": "Juan",
            "monto_total": "500000",
            "fecha": "2026-01-01",
            "garantia": "Reloj",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["garantia"] == "Reloj"


def test_list_deudores_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    client.post(
        "/deudores",
        json={"nombre": "Deudor A", "monto_total": "100000", "fecha": "2026-01-01"},
        headers=headers_a,
    )

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    client.post(
        "/deudores",
        json={"nombre": "Deudor B", "monto_total": "200000", "fecha": "2026-01-01"},
        headers=headers_b,
    )

    response = client.get("/deudores", headers=headers_a)
    nombres = [d["nombre"] for d in response.json()]
    assert nombres == ["Deudor A"]


def test_get_deudor_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    created = client.post(
        "/deudores",
        json={"nombre": "Deudor A", "monto_total": "100000", "fecha": "2026-01-01"},
        headers=headers_a,
    )
    deudor_id = created.json()["id"]

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get(f"/deudores/{deudor_id}", headers=headers_b)
    assert response.status_code == 404


def test_update_deudor_each_field_independently(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/deudores",
        json={"nombre": "Original", "monto_total": "100000", "fecha": "2026-01-01"},
        headers=headers,
    )
    deudor_id = created.json()["id"]

    response = client.patch(f"/deudores/{deudor_id}", json={"nombre": "Actualizado"}, headers=headers)
    assert response.json()["nombre"] == "Actualizado"

    response = client.patch(
        f"/deudores/{deudor_id}", json={"monto_total": "200000"}, headers=headers
    )
    assert response.json()["monto_total"] == "200000.00"

    response = client.patch(f"/deudores/{deudor_id}", json={"fecha": "2026-06-01"}, headers=headers)
    assert response.json()["fecha"] == "2026-06-01"

    response = client.patch(f"/deudores/{deudor_id}", json={"garantia": "Carro"}, headers=headers)
    assert response.json()["garantia"] == "Carro"


def test_close_deudor_with_nonzero_balance(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/deudores",
        json={"nombre": "Juan", "monto_total": "500000", "fecha": "2026-01-01"},
        headers=headers,
    )
    deudor_id = created.json()["id"]

    response = client.patch(f"/deudores/{deudor_id}", json={"activo": False}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["activo"] is False
    assert response.json()["saldo_restante"] == "500000.00"


def test_delete_deudor_cascades_abonos(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/deudores",
        json={"nombre": "Juan", "monto_total": "500000", "fecha": "2026-01-01"},
        headers=headers,
    )
    deudor_id = created.json()["id"]
    client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "100000", "fecha": "2026-02-01"},
        headers=headers,
    )

    response = client.delete(f"/deudores/{deudor_id}", headers=headers)
    assert response.status_code == 204

    get = client.get(f"/deudores/{deudor_id}", headers=headers)
    assert get.status_code == 404


def test_saldo_restante_no_abonos(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/deudores",
        json={"nombre": "Juan", "monto_total": "500000", "fecha": "2026-01-01"},
        headers=headers,
    )
    assert created.json()["saldo_restante"] == "500000.00"


def test_saldo_restante_partial_abonos(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/deudores",
        json={"nombre": "Juan", "monto_total": "500000", "fecha": "2026-01-01"},
        headers=headers,
    )
    deudor_id = created.json()["id"]
    client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "100000", "fecha": "2026-02-01"},
        headers=headers,
    )
    client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "50000", "fecha": "2026-03-01"},
        headers=headers,
    )

    response = client.get(f"/deudores/{deudor_id}", headers=headers)
    assert response.json()["saldo_restante"] == "350000.00"


def test_saldo_restante_fully_paid(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/deudores",
        json={"nombre": "Juan", "monto_total": "500000", "fecha": "2026-01-01"},
        headers=headers,
    )
    deudor_id = created.json()["id"]
    client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "500000", "fecha": "2026-02-01"},
        headers=headers,
    )

    response = client.get(f"/deudores/{deudor_id}", headers=headers)
    assert response.json()["saldo_restante"] == "0.00"


def test_abono_with_interes_recorded(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/deudores",
        json={"nombre": "Juan", "monto_total": "500000", "fecha": "2026-01-01"},
        headers=headers,
    )
    deudor_id = created.json()["id"]
    response = client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "110000", "fecha": "2026-02-01", "interes": "10000"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["interes"] == "10000.00"


def test_abono_interes_cannot_exceed_monto(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/deudores",
        json={"nombre": "Juan", "monto_total": "500000", "fecha": "2026-01-01"},
        headers=headers,
    )
    deudor_id = created.json()["id"]
    response = client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "100000", "fecha": "2026-02-01", "interes": "150000"},
        headers=headers,
    )
    assert response.status_code == 422


def test_saldo_restante_excludes_interest_portion(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    created = client.post(
        "/deudores",
        json={"nombre": "Juan", "monto_total": "500000", "fecha": "2026-01-01"},
        headers=headers,
    )
    deudor_id = created.json()["id"]
    client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "110000", "fecha": "2026-02-01", "interes": "10000"},
        headers=headers,
    )

    response = client.get(f"/deudores/{deudor_id}", headers=headers)
    # Only the 100000 principal portion reduces the balance, not the full 110000.
    assert response.json()["saldo_restante"] == "400000.00"


def test_finalizado_en_set_on_close_and_cleared_on_reactivate(client: TestClient, monkeypatch):
    import datetime

    headers = _headers(client, monkeypatch)
    created = client.post(
        "/deudores",
        json={"nombre": "Juan", "monto_total": "500000", "fecha": "2026-01-01"},
        headers=headers,
    )
    deudor_id = created.json()["id"]
    assert created.json()["finalizado_en"] is None

    closed = client.patch(f"/deudores/{deudor_id}", json={"activo": False}, headers=headers)
    assert closed.status_code == 200, closed.text
    assert closed.json()["finalizado_en"] == datetime.date.today().isoformat()

    reactivated = client.patch(f"/deudores/{deudor_id}", json={"activo": True}, headers=headers)
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["finalizado_en"] is None
