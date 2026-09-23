import json
import secrets
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.models.concepto import PeriodoTasa, TipoConcepto
from app.models.user import User
from app.models.whatsapp_session import WhatsAppSession
from app.schemas.agent import (
    ChatMessage,
    ChatResponse,
    ClarificationNeededResponse,
    ProposedActionResponse,
    ReplyResponse,
)
from app.services import agent_service, concept_service, gasto_service

PENDING_TTL_MINUTES = 20

_AFFIRMATIVE = {"si", "s", "sí", "dale", "confirmar", "confirmo", "ok", "vale", "listo", "1", "yes"}
_NEGATIVE = {"no", "n", "cancelar", "cancela", "2"}


def _normalize(text: str) -> str:
    stripped = text.strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", stripped) if unicodedata.category(c) != "Mn")


def _today_colombia() -> date:
    return datetime.now(ZoneInfo("America/Bogota")).date()


def generate_link_token(session: Session, user: User) -> str:
    """Regenerates the one-time secret sent as the wa.me prefilled message
    body to link a phone number to this account. Mirrors ics_token's shape -
    see User.whatsapp_link_token."""
    token = secrets.token_urlsafe(16)
    user.whatsapp_link_token = token
    session.add(user)
    session.commit()
    return token


def unlink(session: Session, user: User) -> None:
    user.whatsapp_phone = None
    user.whatsapp_link_token = None
    session.add(user)
    session.commit()


def resolve_link(session: Session, phone_number: str, message_body: str) -> User | None:
    """If message_body matches a live whatsapp_link_token, links phone_number
    to that user (single use - the token is cleared) and returns the user;
    otherwise None."""
    token = message_body.strip()
    if not token:
        return None
    user = session.exec(select(User).where(User.whatsapp_link_token == token)).first()
    if user is None:
        return None
    user.whatsapp_phone = phone_number
    user.whatsapp_link_token = None
    session.add(user)
    session.commit()
    return user


def get_user_by_phone(session: Session, phone_number: str) -> User | None:
    return session.exec(select(User).where(User.whatsapp_phone == phone_number)).first()


def _utcnow_naive() -> datetime:
    # The expires_at column is a plain DateTime (no timezone=True - matches
    # every other datetime column in this codebase, e.g. User.created_at),
    # so Postgres and SQLite alike store and return naive values. Comparing
    # against an aware datetime.now(timezone.utc) would raise, so this stays
    # naive UTC throughout instead of round-tripping tzinfo through storage.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_pending(session: Session, phone_number: str) -> WhatsAppSession | None:
    row = session.get(WhatsAppSession, phone_number)
    if row is None:
        return None
    if row.expires_at is None or row.expires_at < _utcnow_naive():
        session.delete(row)
        session.commit()
        return None
    return row


def _set_pending(
    session: Session, phone_number: str, response: ChatResponse, *, original_message: str | None
) -> None:
    row = session.get(WhatsAppSession, phone_number)
    if row is None:
        row = WhatsAppSession(phone_number=phone_number)
    row.pending_response_json = response.model_dump_json()
    row.pending_original_message = original_message
    row.expires_at = _utcnow_naive() + timedelta(minutes=PENDING_TTL_MINUTES)
    session.add(row)
    session.commit()


def _clear_pending(session: Session, phone_number: str) -> None:
    row = session.get(WhatsAppSession, phone_number)
    if row is not None:
        session.delete(row)
        session.commit()


def _describe_proposal(response: ProposedActionResponse) -> str:
    f = response.fields
    if response.entity == "gasto":
        return f"Gasto: {f.get('descripcion')} — ${f.get('monto')} el {f.get('fecha')}"
    if response.entity == "concepto":
        tipo_label = {"deuda": "Deuda", "gasto_fijo": "Pago fijo", "ingreso": "Ingreso"}
        parts = [f"{tipo_label.get(f.get('tipo'), 'Concepto')}: {f.get('nombre')}"]
        if f.get("valor_total"):
            parts.append(f"por ${f['valor_total']}")
        if f.get("monto_planeado"):
            parts.append(f"(${f['monto_planeado']}/mes)")
        if f.get("duracion_meses"):
            meses = f["duracion_meses"]
            parts.append(f"· {meses} {'mes' if meses == 1 else 'meses'}")
        return " ".join(parts)
    return "Acción reconocida"


def _execute_proposed_action(session: Session, user: User, response: ProposedActionResponse) -> None:
    f = response.fields
    if response.entity == "gasto":
        gasto_service.create_gasto(
            session,
            user.id,
            monto=Decimal(f["monto"]),
            fecha=date.fromisoformat(f["fecha"]),
            descripcion=f["descripcion"],
            categoria_ids=None,
        )
        return
    if response.entity == "concepto":
        concept_service.create_concepto_and_seed_entry(
            session,
            user.id,
            f["nombre"],
            TipoConcepto(f["tipo"]),
            None,
            Decimal(f["valor_total"]) if f.get("valor_total") is not None else None,
            tasa_interes=Decimal(f["tasa_interes"]) if f.get("tasa_interes") is not None else None,
            periodo_tasa=PeriodoTasa(f["periodo_tasa"]) if f.get("periodo_tasa") is not None else None,
            numero_cuotas=f.get("numero_cuotas"),
            dia_vencimiento=f.get("dia_vencimiento"),
            duracion_meses=f.get("duracion_meses"),
            monto_planeado=Decimal(f["monto_planeado"]) if f.get("monto_planeado") is not None else None,
        )
        return
    raise ValueError(f"unsupported entity for WhatsApp: {response.entity}")


def _run_agent_and_store(
    session: Session,
    user: User,
    phone_number: str,
    messages: list[ChatMessage],
    audio: tuple[bytes, str] | None,
) -> str:
    try:
        response = agent_service.chat(session, user, messages, _today_colombia(), audio=audio)
    except agent_service.GeminiUnavailableError:
        return "Tuve un problema entendiendo tu mensaje, intenta de nuevo en un momento."

    if isinstance(response, ProposedActionResponse):
        _set_pending(session, phone_number, response, original_message=None)
        return f"{_describe_proposal(response)}\n\n¿Confirmo? Responde *sí* o *no*."
    if isinstance(response, ClarificationNeededResponse):
        original = messages[0].content if messages else ""
        _set_pending(session, phone_number, response, original_message=original)
        return response.message
    return response.message


def handle_incoming(
    session: Session, phone_number: str, text: str | None, audio: tuple[bytes, str] | None
) -> str:
    """Orchestrates one inbound WhatsApp message end to end - see design.md
    (add-whatsapp-agent). Returns the reply text to send back."""
    user = get_user_by_phone(session, phone_number)
    if user is None:
        if text and resolve_link(session, phone_number, text) is not None:
            return "¡Listo! Tu número quedó conectado a TOBE 🎉. Ya puedes mandarme tus gastos e ingresos."
        return "No reconozco este número. Abre TOBE → Perfil → Conectar WhatsApp para vincularlo."

    pending = _get_pending(session, phone_number)
    if pending is not None and pending.pending_response_json is not None:
        parsed = json.loads(pending.pending_response_json)

        if parsed.get("type") == "proposed_action" and text is not None:
            normalized = _normalize(text)
            if normalized in _AFFIRMATIVE:
                response = ProposedActionResponse.model_validate(parsed)
                _execute_proposed_action(session, user, response)
                _clear_pending(session, phone_number)
                return "Listo, registrado ✅."
            if normalized in _NEGATIVE:
                _clear_pending(session, phone_number)
                return "Cancelado."
            _clear_pending(session, phone_number)
            # Falls through below - treated as a brand new message.

        elif parsed.get("type") == "clarification_needed":
            original_message = pending.pending_original_message or ""
            _clear_pending(session, phone_number)
            mini_messages = [
                ChatMessage(role="user", content=original_message),
                ChatMessage(role="model", content=parsed.get("message", "")),
                ChatMessage(role="user", content=text or ""),
            ]
            return _run_agent_and_store(session, user, phone_number, mini_messages, audio)

        else:
            _clear_pending(session, phone_number)

    return _run_agent_and_store(session, user, phone_number, [ChatMessage(role="user", content=text or "")], audio)
