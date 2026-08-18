from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def _create_deudor(client: TestClient, headers) -> int:
    created = client.post(
        "/deudores",
        json={"nombre": "Juan", "monto_total": "500000", "fecha": "2026-01-01"},
        headers=headers,
    )
    return created.json()["id"]


def test_create_abono_reduces_saldo_restante(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor_id = _create_deudor(client, headers)

    response = client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "150000", "fecha": "2026-02-01"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["monto"] == "150000.00"

    deudor = client.get(f"/deudores/{deudor_id}", headers=headers)
    assert deudor.json()["saldo_restante"] == "350000.00"


def test_create_abono_against_another_users_deudor_returns_404(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    deudor_id = _create_deudor(client, headers_a)

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "1000", "fecha": "2026-02-01"},
        headers=headers_b,
    )
    assert response.status_code == 404


def test_list_abonos_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    deudor_id = _create_deudor(client, headers_a)
    client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "1000", "fecha": "2026-02-01"},
        headers=headers_a,
    )

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.get(f"/deudores/{deudor_id}/abonos", headers=headers_b)
    assert response.status_code == 404


def test_delete_abono_restores_saldo_restante(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    deudor_id = _create_deudor(client, headers)
    abono = client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "150000", "fecha": "2026-02-01"},
        headers=headers,
    )
    abono_id = abono.json()["id"]

    delete = client.delete(f"/deudores/{deudor_id}/abonos/{abono_id}", headers=headers)
    assert delete.status_code == 204

    deudor = client.get(f"/deudores/{deudor_id}", headers=headers)
    assert deudor.json()["saldo_restante"] == "500000.00"


def test_delete_abono_from_another_users_deudor_returns_404(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    deudor_id = _create_deudor(client, headers_a)
    abono = client.post(
        f"/deudores/{deudor_id}/abonos",
        json={"monto": "1000", "fecha": "2026-02-01"},
        headers=headers_a,
    )
    abono_id = abono.json()["id"]

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.delete(f"/deudores/{deudor_id}/abonos/{abono_id}", headers=headers_b)
    assert response.status_code == 404
