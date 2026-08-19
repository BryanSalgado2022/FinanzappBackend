from datetime import date

import app.services.agent_service as agent_service
from app.models.deudor import Deudor
from tests.conftest import auth_headers


class FakeFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class FakeResponse:
    def __init__(self, function_calls=None, text=None):
        self.function_calls = function_calls or []
        self.text = text


class FakeModels:
    def __init__(self, response):
        self._response = response

    def generate_content(self, **kwargs):
        return self._response


class FakeClient:
    def __init__(self, response):
        self.models = FakeModels(response)


def _mock_gemini(monkeypatch, response=None, raise_error=False):
    def fake_client(api_key):
        if raise_error:
            raise RuntimeError("boom")
        return FakeClient(response)

    monkeypatch.setattr(agent_service.genai, "Client", fake_client)


def _chat(client, headers, text):
    return client.post(
        "/agent/chat",
        headers=headers,
        json={"messages": [{"role": "user", "content": text}], "current_date": "2026-08-19"},
    )


def test_complete_message_produces_proposed_action(client, monkeypatch):
    headers = auth_headers(client, monkeypatch, sub="a", email="a@x.com", name="A")
    _mock_gemini(
        monkeypatch,
        FakeResponse(
            function_calls=[
                FakeFunctionCall(
                    "crear_gasto",
                    {"monto": "50000", "fecha": "2026-08-19", "descripcion": "gasolina"},
                )
            ]
        ),
    )
    response = _chat(client, headers, "Hoy gasté 50.000 en gasolina para el carro")
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "proposed_action"
    assert body["entity"] == "gasto"
    assert body["fields"] == {"monto": "50000", "fecha": "2026-08-19", "descripcion": "gasolina"}


def test_incomplete_message_asks_for_clarification(client, monkeypatch):
    headers = auth_headers(client, monkeypatch, sub="b", email="b@x.com", name="B")
    _mock_gemini(
        monkeypatch,
        FakeResponse(
            function_calls=[FakeFunctionCall("pedir_aclaracion", {"pregunta": "¿Cuánto le abonaste?"})]
        ),
    )
    response = _chat(client, headers, "Le aboné a Juan")
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "clarification_needed"
    assert "abonaste" in body["message"]


def test_unrelated_message_gets_plain_reply(client, monkeypatch):
    headers = auth_headers(client, monkeypatch, sub="c", email="c@x.com", name="C")
    _mock_gemini(monkeypatch, FakeResponse(text="Puedo ayudarte a registrar gastos y más."))
    response = _chat(client, headers, "¿Qué tiempo hace hoy?")
    assert response.status_code == 200
    assert response.json()["type"] == "reply"


def test_abono_resolves_exact_debtor_match(client, monkeypatch, session):
    headers = auth_headers(client, monkeypatch, sub="d", email="d@x.com", name="D")
    me = client.get("/users/me", headers=headers).json()
    deudor = Deudor(user_id=me["id"], nombre="Juan Pérez", monto_total="100000", fecha=date(2026, 1, 1))
    session.add(deudor)
    session.commit()
    session.refresh(deudor)

    _mock_gemini(
        monkeypatch,
        FakeResponse(
            function_calls=[
                FakeFunctionCall(
                    "crear_abono",
                    {"deudor_nombre": "Juan", "monto": "20000", "fecha": "2026-08-19"},
                )
            ]
        ),
    )
    response = _chat(client, headers, "Juan me abonó 20.000 hoy")
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "proposed_action"
    assert body["entity"] == "abono"
    assert body["fields"]["deudor_id"] == deudor.id


def test_abono_with_no_matching_debtor_asks_for_clarification(client, monkeypatch):
    headers = auth_headers(client, monkeypatch, sub="e", email="e@x.com", name="E")
    _mock_gemini(
        monkeypatch,
        FakeResponse(
            function_calls=[
                FakeFunctionCall(
                    "crear_abono",
                    {"deudor_nombre": "Nadie", "monto": "1000", "fecha": "2026-08-19"},
                )
            ]
        ),
    )
    response = _chat(client, headers, "Nadie me abonó 1.000")
    assert response.status_code == 200
    assert response.json()["type"] == "clarification_needed"


def test_abono_with_ambiguous_debtor_asks_for_clarification(client, monkeypatch, session):
    headers = auth_headers(client, monkeypatch, sub="f", email="f@x.com", name="F")
    me = client.get("/users/me", headers=headers).json()
    session.add(Deudor(user_id=me["id"], nombre="Juan Pérez", monto_total="1", fecha=date(2026, 1, 1)))
    session.add(Deudor(user_id=me["id"], nombre="Juan Gómez", monto_total="1", fecha=date(2026, 1, 1)))
    session.commit()

    _mock_gemini(
        monkeypatch,
        FakeResponse(
            function_calls=[
                FakeFunctionCall(
                    "crear_abono", {"deudor_nombre": "Juan", "monto": "1000", "fecha": "2026-08-19"}
                )
            ]
        ),
    )
    response = _chat(client, headers, "Juan me abonó 1.000")
    assert response.status_code == 200
    assert response.json()["type"] == "clarification_needed"


def test_unauthenticated_request_is_rejected(client):
    response = client.post(
        "/agent/chat",
        json={"messages": [{"role": "user", "content": "hola"}], "current_date": "2026-08-19"},
    )
    assert response.status_code == 401


def test_debtor_resolution_is_scoped_to_the_authenticated_user(client, monkeypatch, session):
    other_headers = auth_headers(client, monkeypatch, sub="g", email="g@x.com", name="G")
    other_me = client.get("/users/me", headers=other_headers).json()
    session.add(
        Deudor(user_id=other_me["id"], nombre="Juan Pérez", monto_total="1", fecha=date(2026, 1, 1))
    )
    session.commit()

    my_headers = auth_headers(client, monkeypatch, sub="h", email="h@x.com", name="H")
    _mock_gemini(
        monkeypatch,
        FakeResponse(
            function_calls=[
                FakeFunctionCall(
                    "crear_abono", {"deudor_nombre": "Juan", "monto": "1000", "fecha": "2026-08-19"}
                )
            ]
        ),
    )
    response = _chat(client, my_headers, "Juan me abonó 1.000")
    assert response.status_code == 200
    # Another user's debtor named Juan must not resolve for me.
    assert response.json()["type"] == "clarification_needed"


def test_gemini_failure_returns_502(client, monkeypatch):
    headers = auth_headers(client, monkeypatch, sub="i", email="i@x.com", name="I")
    _mock_gemini(monkeypatch, raise_error=True)
    response = _chat(client, headers, "Hoy gasté 5.000 en café")
    assert response.status_code == 502


def test_rate_limit_trips_after_threshold(client, monkeypatch):
    headers = auth_headers(client, monkeypatch, sub="j", email="j@x.com", name="J")
    _mock_gemini(monkeypatch, FakeResponse(text="ok"))
    for _ in range(20):
        assert _chat(client, headers, "hola").status_code == 200
    assert _chat(client, headers, "hola").status_code == 429
