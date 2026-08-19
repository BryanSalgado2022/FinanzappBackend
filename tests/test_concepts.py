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


def test_create_seeds_explicit_year_month_not_server_today(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/concepts",
        json={
            "nombre": "Prima",
            "tipo": "ingreso",
            "monto_planeado": "500000",
            "anio": 2027,
            "mes": 3,
        },
        headers=headers,
    )
    concept_id = response.json()["id"]

    entries = client.get(f"/concepts/{concept_id}/entries", headers=headers).json()
    assert [(e["anio"], e["mes"]) for e in entries] == [(2027, 3)]


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


def test_create_debt_and_fixed_expense_with_due_day(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    for tipo in ("deuda", "gasto_fijo"):
        response = client.post(
            "/concepts",
            json={"nombre": tipo, "tipo": tipo, "dia_vencimiento": 15},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        assert response.json()["dia_vencimiento"] == 15


def test_reject_dia_vencimiento_out_of_range(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    for dia in (0, 29):
        response = client.post(
            "/concepts",
            json={"nombre": "Gasto", "tipo": "gasto_fijo", "dia_vencimiento": dia},
            headers=headers,
        )
        assert response.status_code == 422


def test_dia_vencimiento_accepted_on_ingreso(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/concepts",
        json={"nombre": "Sueldo", "tipo": "ingreso", "dia_vencimiento": 15},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["dia_vencimiento"] == 15

    concept_id = response.json()["id"]
    update = client.patch(
        f"/concepts/{concept_id}", json={"dia_vencimiento": 20}, headers=headers
    )
    assert update.status_code == 200, update.text
    assert update.json()["dia_vencimiento"] == 20


def test_dia_vencimiento_editable_even_on_amortized_debt(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    create = client.post(
        "/concepts",
        json={
            "nombre": "Credito",
            "tipo": "deuda",
            "valor_total": "1000000",
            "tasa_interes": "1.5",
            "numero_cuotas": 12,
        },
        headers=headers,
    )
    concept_id = create.json()["id"]

    response = client.patch(
        f"/concepts/{concept_id}", json={"dia_vencimiento": 20}, headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["dia_vencimiento"] == 20


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


def test_create_concept_with_categoria_ids(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    categoria = client.post("/categorias", json={"nombre": "Vivienda"}, headers=headers).json()

    response = client.post(
        "/concepts",
        json={"nombre": "Renta", "tipo": "gasto_fijo", "categoria_ids": [categoria["id"]]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert [c["nombre"] for c in response.json()["categorias"]] == ["Vivienda"]


def test_create_concept_without_categoria_ids_has_no_categories(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/concepts", json={"nombre": "Renta", "tipo": "gasto_fijo"}, headers=headers
    )
    assert response.status_code == 201, response.text
    assert response.json()["categorias"] == []


def test_create_concept_rejects_unknown_categoria_id(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    response = client.post(
        "/concepts",
        json={"nombre": "Renta", "tipo": "gasto_fijo", "categoria_ids": [999999]},
        headers=headers,
    )
    assert response.status_code == 422


def test_create_concept_rejects_categoria_id_from_another_user(client: TestClient, monkeypatch):
    headers_a = auth_headers(client, monkeypatch, sub="google-a", email="a@example.com", name="A")
    categoria = client.post("/categorias", json={"nombre": "Vivienda"}, headers=headers_a).json()

    headers_b = auth_headers(client, monkeypatch, sub="google-b", email="b@example.com", name="B")
    response = client.post(
        "/concepts",
        json={"nombre": "Renta", "tipo": "gasto_fijo", "categoria_ids": [categoria["id"]]},
        headers=headers_b,
    )
    assert response.status_code == 422


def test_update_concept_replaces_categoria_ids(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    cat_a = client.post("/categorias", json={"nombre": "Vivienda"}, headers=headers).json()
    cat_b = client.post("/categorias", json={"nombre": "Creditos"}, headers=headers).json()
    concept = client.post(
        "/concepts",
        json={"nombre": "Renta", "tipo": "gasto_fijo", "categoria_ids": [cat_a["id"]]},
        headers=headers,
    ).json()

    response = client.patch(
        f"/concepts/{concept['id']}", json={"categoria_ids": [cat_b["id"]]}, headers=headers
    )
    assert response.status_code == 200, response.text
    assert [c["nombre"] for c in response.json()["categorias"]] == ["Creditos"]


def test_update_concept_omitted_categoria_ids_leaves_assignments_unchanged(
    client: TestClient, monkeypatch
):
    headers = _headers(client, monkeypatch)
    categoria = client.post("/categorias", json={"nombre": "Vivienda"}, headers=headers).json()
    concept = client.post(
        "/concepts",
        json={"nombre": "Renta", "tipo": "gasto_fijo", "categoria_ids": [categoria["id"]]},
        headers=headers,
    ).json()

    response = client.patch(f"/concepts/{concept['id']}", json={"nombre": "Renta 2"}, headers=headers)
    assert response.status_code == 200, response.text
    assert [c["nombre"] for c in response.json()["categorias"]] == ["Vivienda"]


def test_update_concept_empty_categoria_ids_clears_assignments(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    categoria = client.post("/categorias", json={"nombre": "Vivienda"}, headers=headers).json()
    concept = client.post(
        "/concepts",
        json={"nombre": "Renta", "tipo": "gasto_fijo", "categoria_ids": [categoria["id"]]},
        headers=headers,
    ).json()

    response = client.patch(f"/concepts/{concept['id']}", json={"categoria_ids": []}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["categorias"] == []


def test_finalizado_en_set_on_finish_and_cleared_on_reactivate(client: TestClient, monkeypatch):
    import datetime

    headers = _headers(client, monkeypatch)
    concept = client.post(
        "/concepts", json={"nombre": "Renta", "tipo": "gasto_fijo"}, headers=headers
    ).json()
    assert concept["finalizado_en"] is None

    finished = client.patch(f"/concepts/{concept['id']}", json={"activo": False}, headers=headers)
    assert finished.status_code == 200, finished.text
    assert finished.json()["finalizado_en"] == datetime.date.today().isoformat()

    reactivated = client.patch(f"/concepts/{concept['id']}", json={"activo": True}, headers=headers)
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["finalizado_en"] is None


def test_finalizado_en_unchanged_when_activo_resent_unchanged(client: TestClient, monkeypatch):
    headers = _headers(client, monkeypatch)
    concept = client.post(
        "/concepts", json={"nombre": "Renta", "tipo": "gasto_fijo"}, headers=headers
    ).json()

    response = client.patch(f"/concepts/{concept['id']}", json={"activo": True}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["finalizado_en"] is None
