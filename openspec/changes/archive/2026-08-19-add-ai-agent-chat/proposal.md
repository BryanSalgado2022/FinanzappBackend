## Why

Manually filling out a form for every expense, debt, task, or debtor is friction the user wants to skip for the common case: typing (or eventually speaking) a plain-language sentence like "Hoy gasté 50.000 en gasolina" should be enough. The API already has clean, well-typed creation endpoints for every entity involved - what's missing is a layer that turns free text into the right structured call, asks for whatever's missing, and never writes anything without the user's explicit go-ahead.

## What Changes

- Add `POST /agent/chat`: a stateless endpoint that takes the full conversation history (sent by the caller each time) plus the client's current date, and uses Gemini 3.7 Flash function-calling to interpret the latest message.
- Five tools exposed to the model, one per creatable entity: `crear_gasto`, `crear_concepto`, `crear_tarea`, `crear_deudor`, `crear_abono` - each mapped field-for-field to the existing `*Create` Pydantic schemas (minus `categoria_ids`, out of scope for v1).
- The endpoint **never writes to the database**. When the model calls a tool, the endpoint returns a structured "proposed action" (entity type + extracted fields) instead of executing it. When the model decides it needs more information, it returns a clarifying question instead. A sibling frontend change (`add-ai-agent-chat-ui` in FinanzappFrontend) is what actually executes the write, through the existing REST endpoints, once the user confirms.
- `crear_abono` receives a debtor **name**, not an id - the backend resolves it against the authenticated user's own debtors before responding, and reports back an unresolved/ambiguous match as part of the proposed-action payload rather than guessing.
- New `GEMINI_API_KEY` setting and new `google-genai` dependency (Google's current Gen AI Python SDK).
- Rate-limited the same way `/auth/register` and `/auth/login` already are (`app/services/rate_limit.py`), since each message costs a paid external API call.

## Capabilities

### New Capabilities
- `agent-chat`: a conversational endpoint that turns natural-language messages into proposed (not executed) financial actions, asking for missing required fields before proposing.

### Modified Capabilities
(none - every existing entity-creation endpoint and its validation rules are untouched; this only adds a new way to arrive at the same, unmodified `*Create` payloads)

## Impact

- New: `app/routers/agent.py`, `app/services/agent_service.py`, `app/schemas/agent.py`.
- `app/config.py`: new `gemini_api_key` setting.
- `requirements.txt`: new `google-genai` dependency.
- `.env.example`, `README.md` "Despliegue" section: document `GEMINI_API_KEY`.
- No changes to any existing router, service, schema, or model - the tool definitions read from them but don't modify them.
