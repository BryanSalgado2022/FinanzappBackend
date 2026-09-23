from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session, select
from twilio.request_validator import RequestValidator

import app.services.agent_service as agent_service
from app.models.entrada_mensual import EntradaMensual
from app.models.gasto import Gasto
from app.models.user import User
from app.models.whatsapp_session import WhatsAppSession
from app.services import whatsapp_service
from tests.conftest import auth_headers

WEBHOOK_URL = "http://testserver/whatsapp/webhook"
TWILIO_AUTH_TOKEN = "test-twilio-auth-token"


def _headers(client: TestClient, monkeypatch):
    return auth_headers(client, monkeypatch, sub="google-1", email="a@example.com", name="Ana")


def _get_user(session: Session, client: TestClient, headers: dict) -> User:
    me = client.get("/users/me", headers=headers).json()
    return session.get(User, me["id"])


# --- Gemini mocking, mirrors tests/test_agent.py -----------------------------


class FakeFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class FakeResponse:
    def __init__(self, function_calls=None, text=None):
        self.function_calls = function_calls or []
        self.text = text


class FakeModels:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, models):
        self.models = models


def _mock_gemini(monkeypatch, *responses):
    models = FakeModels(responses)

    def fake_client(api_key):
        return FakeClient(models)

    monkeypatch.setattr(agent_service.genai, "Client", fake_client)
    return models


# --- Twilio webhook test helpers --------------------------------------------


def _sign(params: dict) -> str:
    return RequestValidator(TWILIO_AUTH_TOKEN).compute_signature(WEBHOOK_URL, params)


def _post_webhook(client: TestClient, params: dict, *, signature: str | None = None):
    return client.post(
        "/whatsapp/webhook",
        data=params,
        headers={"X-Twilio-Signature": signature if signature is not None else _sign(params)},
    )


# --- Linking -----------------------------------------------------------------


def test_generate_link_token_and_resolve_link(client: TestClient, monkeypatch, session: Session):
    headers = _headers(client, monkeypatch)
    user = _get_user(session, client, headers)

    token = whatsapp_service.generate_link_token(session, user)
    linked = whatsapp_service.resolve_link(session, "+573001112222", token)

    assert linked is not None
    assert linked.id == user.id
    session.refresh(user)
    assert user.whatsapp_phone == "+573001112222"
    assert user.whatsapp_link_token is None


def test_resolve_link_with_wrong_token_returns_none(session: Session):
    assert whatsapp_service.resolve_link(session, "+573001112222", "not-a-real-token") is None


def test_token_is_single_use(client: TestClient, monkeypatch, session: Session):
    headers = _headers(client, monkeypatch)
    user = _get_user(session, client, headers)
    token = whatsapp_service.generate_link_token(session, user)

    whatsapp_service.resolve_link(session, "+573001112222", token)
    second_attempt = whatsapp_service.resolve_link(session, "+573009998888", token)

    assert second_attempt is None


def test_unlinked_number_gets_instructions(session: Session):
    reply = whatsapp_service.handle_incoming(session, "+573000000000", "hola", None)
    assert "vincularlo" in reply.lower()


# --- Proposal + confirmation ---------------------------------------------------


def _link(session: Session, user: User, phone: str) -> None:
    token = whatsapp_service.generate_link_token(session, user)
    whatsapp_service.resolve_link(session, phone, token)


def test_complete_message_produces_proposal_not_write(client: TestClient, monkeypatch, session: Session):
    headers = _headers(client, monkeypatch)
    user = _get_user(session, client, headers)
    _link(session, user, "+573001112222")
    _mock_gemini(
        monkeypatch,
        FakeResponse(
            function_calls=[
                FakeFunctionCall("crear_gasto", {"monto": "50000", "fecha": "2026-09-23", "descripcion": "almuerzo"})
            ]
        ),
    )

    reply = whatsapp_service.handle_incoming(session, "+573001112222", "gasté 50.000 en almuerzo", None)

    assert "50000" in reply or "50.000" in reply
    assert session.exec(select(Gasto).where(Gasto.user_id == user.id)).first() is None
    assert session.get(WhatsAppSession, "+573001112222") is not None


def test_affirmative_reply_creates_the_gasto(client: TestClient, monkeypatch, session: Session):
    headers = _headers(client, monkeypatch)
    user = _get_user(session, client, headers)
    _link(session, user, "+573001112222")
    _mock_gemini(
        monkeypatch,
        FakeResponse(
            function_calls=[
                FakeFunctionCall("crear_gasto", {"monto": "50000", "fecha": "2026-09-23", "descripcion": "almuerzo"})
            ]
        ),
    )
    whatsapp_service.handle_incoming(session, "+573001112222", "gasté 50.000 en almuerzo", None)

    reply = whatsapp_service.handle_incoming(session, "+573001112222", "si", None)

    assert "registrado" in reply.lower()
    gasto = session.exec(select(Gasto).where(Gasto.user_id == user.id)).first()
    assert gasto is not None
    assert gasto.descripcion == "almuerzo"
    assert session.get(WhatsAppSession, "+573001112222") is None


def test_negative_reply_discards_pending(client: TestClient, monkeypatch, session: Session):
    headers = _headers(client, monkeypatch)
    user = _get_user(session, client, headers)
    _link(session, user, "+573001112222")
    _mock_gemini(
        monkeypatch,
        FakeResponse(
            function_calls=[
                FakeFunctionCall("crear_gasto", {"monto": "50000", "fecha": "2026-09-23", "descripcion": "almuerzo"})
            ]
        ),
    )
    whatsapp_service.handle_incoming(session, "+573001112222", "gasté 50.000 en almuerzo", None)

    reply = whatsapp_service.handle_incoming(session, "+573001112222", "no", None)

    assert "cancelado" in reply.lower()
    assert session.exec(select(Gasto).where(Gasto.user_id == user.id)).first() is None
    assert session.get(WhatsAppSession, "+573001112222") is None


def test_unrecognized_reply_discards_and_is_processed_as_new_message(
    client: TestClient, monkeypatch, session: Session
):
    headers = _headers(client, monkeypatch)
    user = _get_user(session, client, headers)
    _link(session, user, "+573001112222")
    _mock_gemini(
        monkeypatch,
        FakeResponse(
            function_calls=[
                FakeFunctionCall("crear_gasto", {"monto": "50000", "fecha": "2026-09-23", "descripcion": "almuerzo"})
            ]
        ),
        FakeResponse(
            function_calls=[
                FakeFunctionCall("crear_gasto", {"monto": "10000", "fecha": "2026-09-23", "descripcion": "cafe"})
            ]
        ),
    )
    whatsapp_service.handle_incoming(session, "+573001112222", "gasté 50.000 en almuerzo", None)

    reply = whatsapp_service.handle_incoming(session, "+573001112222", "tambien gasté 10.000 en cafe", None)

    assert "10000" in reply or "10.000" in reply
    assert "cafe" in reply


# --- Clarification continuation ------------------------------------------------


def test_clarification_then_answer_is_understood_in_context(client: TestClient, monkeypatch, session: Session):
    headers = _headers(client, monkeypatch)
    user = _get_user(session, client, headers)
    _link(session, user, "+573001112222")
    models = _mock_gemini(
        monkeypatch,
        FakeResponse(function_calls=[FakeFunctionCall("pedir_aclaracion", {"pregunta": "¿Cuánto gastaste?"})]),
        FakeResponse(
            function_calls=[
                FakeFunctionCall("crear_gasto", {"monto": "20000", "fecha": "2026-09-23", "descripcion": "bus"})
            ]
        ),
    )

    first_reply = whatsapp_service.handle_incoming(session, "+573001112222", "gasté en el bus", None)
    assert "cuanto" in first_reply.lower() or "cuánto" in first_reply.lower()

    second_reply = whatsapp_service.handle_incoming(session, "+573001112222", "20 mil", None)

    assert "20000" in second_reply or "20.000" in second_reply
    # The second Gemini call was given the reconstructed mini-context, not
    # just the bare follow-up message in isolation.
    second_call_contents = models.calls[1]["contents"]
    assert len(second_call_contents) == 3
    assert second_call_contents[0].parts[0].text == "gasté en el bus"
    assert second_call_contents[2].parts[0].text == "20 mil"


# --- Expiry ---------------------------------------------------------------------


def test_expired_pending_is_treated_as_new_message(client: TestClient, monkeypatch, session: Session):
    headers = _headers(client, monkeypatch)
    user = _get_user(session, client, headers)
    _link(session, user, "+573001112222")
    session.add(
        WhatsAppSession(
            phone_number="+573001112222",
            pending_response_json='{"type":"proposed_action","entity":"gasto","fields":{"monto":"999999","fecha":"2026-01-01","descripcion":"viejo"}}',
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
    )
    session.commit()
    _mock_gemini(monkeypatch, FakeResponse(text="No entendí ese mensaje."))

    reply = whatsapp_service.handle_incoming(session, "+573001112222", "si", None)

    assert session.exec(select(Gasto).where(Gasto.user_id == user.id)).first() is None
    assert reply == "No entendí ese mensaje."


# --- duracion_meses ------------------------------------------------------------


def test_concepto_with_duracion_meses_creates_exactly_that_many_entries(
    client: TestClient, monkeypatch, session: Session
):
    headers = _headers(client, monkeypatch)
    user = _get_user(session, client, headers)
    _link(session, user, "+573001112222")
    _mock_gemini(
        monkeypatch,
        FakeResponse(
            function_calls=[
                FakeFunctionCall(
                    "crear_concepto",
                    {
                        "nombre": "Regalo cumpleaños",
                        "tipo": "ingreso",
                        "monto_planeado": "100000",
                        "duracion_meses": 1,
                    },
                )
            ]
        ),
    )
    whatsapp_service.handle_incoming(session, "+573001112222", "hoy me llegaron 100.000 de regalo", None)

    whatsapp_service.handle_incoming(session, "+573001112222", "si", None)

    from app.models.concepto import Concepto

    concepto = session.exec(select(Concepto).where(Concepto.user_id == user.id)).first()
    assert concepto is not None
    assert concepto.duracion_meses == 1
    entries = session.exec(select(EntradaMensual).where(EntradaMensual.concepto_id == concepto.id)).all()
    assert len(entries) == 1


# --- Webhook signature verification and rate limiting --------------------------


def test_webhook_rejects_invalid_signature(client: TestClient):
    params = {"From": "whatsapp:+573001112222", "Body": "hola", "NumMedia": "0"}
    response = _post_webhook(client, params, signature="not-a-valid-signature")
    assert response.status_code == 403


def test_webhook_accepts_valid_signature_from_unlinked_number(client: TestClient):
    params = {"From": "whatsapp:+573009998888", "Body": "hola", "NumMedia": "0"}
    response = _post_webhook(client, params)
    assert response.status_code == 200
    assert "vincularlo" in response.text.lower()


def test_webhook_rate_limited_per_phone_number(client: TestClient):
    params = {"From": "whatsapp:+573007776666", "Body": "hola", "NumMedia": "0"}
    for _ in range(20):
        assert _post_webhook(client, params).status_code == 200
    assert _post_webhook(client, params).status_code == 429
