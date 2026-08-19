from datetime import date

from google import genai
from google.genai import types
from sqlmodel import Session, select

from app.config import get_settings
from app.models.deudor import Deudor
from app.models.user import User
from app.schemas.agent import (
    ChatMessage,
    ChatResponse,
    ClarificationNeededResponse,
    ProposedActionResponse,
    ReplyResponse,
)

MODEL = "gemini-3.7-flash"

TOOLS = [
    types.FunctionDeclaration(
        name="crear_gasto",
        description="Registra un gasto puntual/variable (una compra, un pago único).",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "monto": {"type": "string", "description": "Monto del gasto, solo números"},
                "fecha": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                "descripcion": {"type": "string", "description": "En qué se gastó"},
            },
            "required": ["monto", "fecha", "descripcion"],
        },
    ),
    types.FunctionDeclaration(
        name="crear_concepto",
        description=(
            "Registra un concepto recurrente: una deuda (con o sin amortización), "
            "un gasto fijo mensual, o un ingreso."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre del concepto"},
                "tipo": {"type": "string", "enum": ["deuda", "gasto_fijo", "ingreso"]},
                "valor_total": {
                    "type": "string",
                    "description": "Solo para tipo deuda: el monto total adeudado",
                },
                "monto_planeado": {
                    "type": "string",
                    "description": "Monto planeado del mes actual (si no hay amortización)",
                },
                "tasa_interes": {
                    "type": "string",
                    "description": "Solo para deuda con amortización: tasa de interés, ej 1.47 para 1.47%",
                },
                "periodo_tasa": {"type": "string", "enum": ["mensual", "anual"]},
                "numero_cuotas": {
                    "type": "integer",
                    "description": "Solo para deuda con amortización: número total de cuotas",
                },
                "dia_vencimiento": {
                    "type": "integer",
                    "description": "Día del mes (1-28) en que vence/se paga, opcional",
                },
            },
            "required": ["nombre", "tipo"],
        },
    ),
    types.FunctionDeclaration(
        name="crear_tarea",
        description="Registra un recordatorio o cita genérica, no financiera.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "titulo": {"type": "string"},
                "fecha": {"type": "string", "description": "Fecha en formato YYYY-MM-DD, opcional"},
                "hora": {"type": "string", "description": "Hora en formato HH:MM, opcional"},
                "nota": {"type": "string", "description": "Nota adicional, opcional"},
            },
            "required": ["titulo"],
        },
    ),
    types.FunctionDeclaration(
        name="crear_deudor",
        description="Registra a alguien que le debe dinero al usuario (un préstamo que hizo).",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre de la persona"},
                "monto_total": {"type": "string", "description": "Monto total prestado"},
                "fecha": {"type": "string", "description": "Fecha del préstamo en formato YYYY-MM-DD"},
                "garantia": {"type": "string", "description": "Garantía del préstamo, opcional"},
            },
            "required": ["nombre", "monto_total", "fecha"],
        },
    ),
    types.FunctionDeclaration(
        name="pedir_aclaracion",
        description=(
            "Úsala cuando el mensaje del usuario coincide con una de las acciones disponibles "
            "pero falta un dato requerido - nunca para conversación general."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "pregunta": {"type": "string", "description": "La pregunta a hacerle al usuario"},
            },
            "required": ["pregunta"],
        },
    ),
    types.FunctionDeclaration(
        name="crear_abono",
        description="Registra un abono (pago parcial) recibido de un deudor ya existente.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "deudor_nombre": {"type": "string", "description": "Nombre del deudor que abonó"},
                "monto": {"type": "string", "description": "Monto del abono"},
                "fecha": {"type": "string", "description": "Fecha del abono en formato YYYY-MM-DD"},
            },
            "required": ["deudor_nombre", "monto", "fecha"],
        },
    ),
]

SYSTEM_PROMPT_TEMPLATE = """Eres un asistente que ayuda a registrar movimientos financieros en una app de \
presupuesto personal, a partir de mensajes en lenguaje natural del usuario, en español.

La fecha de hoy (para el usuario) es {current_date}. Usa esta fecha para resolver expresiones \
relativas como "hoy", "ayer", "el 15", etc.

Reglas:
- Si el mensaje del usuario tiene toda la información necesaria para una de las herramientas \
de creación, llama a esa herramienta con los datos extraídos.
- Si el mensaje coincide con una acción pero falta un dato requerido, llama a la herramienta \
`pedir_aclaracion` con una pregunta específica sobre lo que falta - NUNCA llames a una \
herramienta de creación con un dato faltante o inventado.
- Si el mensaje no tiene relación con ninguna de las acciones disponibles (gastos, deudas, \
pagos mensuales, ingresos, tareas, deudores, abonos), responde conversacionalmente en texto \
plano, sin llamar ninguna herramienta.
- Nunca inventes valores para campos que el usuario no mencionó explícitamente, salvo la fecha \
cuando el usuario usa una expresión relativa ("hoy", "ayer").
"""


class GeminiUnavailableError(Exception):
    pass


def _resolve_debtor(session: Session, user: User, nombre: str) -> tuple[int | None, list[str]]:
    """Case-insensitive match against the user's own active debtors.

    Returns (resolved_id, candidate_names). resolved_id is set only when
    exactly one match is found; candidate_names lists what matched (0, or
    2+) for the caller to build a clarifying message.
    """
    rows = session.exec(
        select(Deudor).where(
            Deudor.user_id == user.id,
            Deudor.activo == True,  # noqa: E712
            Deudor.nombre.ilike(f"%{nombre}%"),
        )
    ).all()
    if len(rows) == 1:
        return rows[0].id, []
    return None, [r.nombre for r in rows]


def _build_response(
    session: Session, user: User, function_name: str, args: dict
) -> ChatResponse:
    if function_name == "pedir_aclaracion":
        return ClarificationNeededResponse(message=args["pregunta"])

    if function_name == "crear_abono":
        deudor_id, candidates = _resolve_debtor(session, user, args["deudor_nombre"])
        if deudor_id is None and not candidates:
            return ClarificationNeededResponse(
                message=f"No encontré ningún deudor llamado \"{args['deudor_nombre']}\". "
                "¿Puedes confirmar el nombre exacto, o quieres registrarlo primero como deudor nuevo?"
            )
        if deudor_id is None:
            nombres = ", ".join(candidates)
            return ClarificationNeededResponse(
                message=f"Encontré varios deudores que coinciden con \"{args['deudor_nombre']}\": "
                f"{nombres}. ¿A cuál te refieres?"
            )
        fields = {"deudor_id": deudor_id, "monto": args["monto"], "fecha": args["fecha"]}
        return ProposedActionResponse(entity="abono", fields=fields)

    entity_by_tool = {
        "crear_gasto": "gasto",
        "crear_concepto": "concepto",
        "crear_tarea": "tarea",
        "crear_deudor": "deudor",
    }
    return ProposedActionResponse(entity=entity_by_tool[function_name], fields=args)


def chat(session: Session, user: User, messages: list[ChatMessage], current_date: date) -> ChatResponse:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiUnavailableError("GEMINI_API_KEY is not configured")

    contents = [
        types.Content(role=m.role, parts=[types.Part(text=m.content)]) for m in messages
    ]

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_TEMPLATE.format(current_date=current_date.isoformat()),
                tools=[types.Tool(function_declarations=TOOLS)],
            ),
        )
    except Exception as exc:  # SDK-level network/API errors
        raise GeminiUnavailableError(str(exc)) from exc

    if response.function_calls:
        call = response.function_calls[0]
        return _build_response(session, user, call.name, dict(call.args))

    text = response.text or "No entendí, ¿puedes reformular?"
    return ReplyResponse(message=text)
