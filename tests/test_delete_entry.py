from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def test_delete_entry_on_indefinite_recurring_concept(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts", json={"nombre": "Sueldo", "tipo": "ingreso", "monto_planeado": "5000000"},
        headers=headers,
    )
    concept_id = create.json()["id"]

    client.put(
        f"/concepts/{concept_id}/entries/2026/8",
        json={"monto_planeado": "5000000"},
        headers=headers,
    )
    response = client.delete(f"/concepts/{concept_id}/entries/2026/8", headers=headers)
    assert response.status_code == 204

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    assert not any(e["anio"] == 2026 and e["mes"] == 8 for e in entries)


def test_delete_entry_rejected_on_amortized_debt(client: TestClient, monkeypatch):
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
    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    first = entries[0]

    response = client.delete(
        f"/concepts/{concept_id}/entries/{first['anio']}/{first['mes']}", headers=headers
    )
    assert response.status_code == 409


def test_delete_entry_rejected_on_fixed_duration_concept(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={
            "nombre": "Bono",
            "tipo": "gasto_fijo",
            "monto_planeado": "100000",
            "duracion_meses": 3,
        },
        headers=headers,
    )
    concept_id = create.json()["id"]
    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    first = entries[0]

    response = client.delete(
        f"/concepts/{concept_id}/entries/{first['anio']}/{first['mes']}", headers=headers
    )
    assert response.status_code == 409


def test_delete_nonexistent_entry_returns_404(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts", json={"nombre": "Sueldo", "tipo": "ingreso"}, headers=headers
    )
    concept_id = create.json()["id"]

    response = client.delete(f"/concepts/{concept_id}/entries/2026/8", headers=headers)
    assert response.status_code == 404


def test_delete_entry_for_missing_concept_returns_404(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.delete("/concepts/999999/entries/2026/8", headers=headers)
    assert response.status_code == 404


def test_delete_entry_scoped_to_owner(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    create = client.post(
        "/concepts", json={"nombre": "Sueldo", "tipo": "ingreso", "monto_planeado": "5000000"},
        headers=headers_a,
    )
    concept_id = create.json()["id"]

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.delete(f"/concepts/{concept_id}/entries/2026/8", headers=headers_b)
    assert response.status_code == 404
