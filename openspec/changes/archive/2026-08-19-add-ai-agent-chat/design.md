## Context

See proposal.md - Why. Confirmed via web search (training data on fast-moving SDKs isn't trustworthy): Google's current Python SDK is `google-genai` (PyPI package `google-genai`, successor to the deprecated `google-generativeai`), and the current Flash-tier model is `gemini-3.7-flash` - verify this string is still current at implementation time, the same way `PanelLeftClose`/`PanelLeftOpen` were spot-checked against the installed `lucide-react` version in a recent frontend change; naming conventions for fast-moving model catalogs drift.

Existing `*Create` Pydantic schemas already read (see `app/schemas/gasto.py`, `concepto.py`, `tarea.py`, `deudor.py`): `GastoCreate` (monto, fecha, descripcion, categoria_ids), `ConceptoCreate` (nombre, tipo, valor_total, monto_planeado, tasa_interes/periodo_tasa/numero_cuotas, cuota_inicial, duracion_meses, dia_vencimiento, anio/mes, categoria_ids), `TareaCreate` (titulo, emoji, fecha, hora, nota), `DeudorCreate` (nombre, monto_total, fecha, garantia), `AbonoCreate` (monto, fecha - created via `POST /deudores/{id}/abonos`, so the id is path-scoped, not part of the body).

## Goals / Non-Goals

**Goals:**
- One stateless endpoint, one call to Gemini per user message, five tools covering every creatable entity except category assignment.
- The response shape is unambiguous about which of three things happened: proposed action, clarifying question, or plain reply - the frontend change needs to switch on this reliably.
- Zero risk of a write happening without human confirmation, by construction (the tool "execution" is just returning data - there's no code path in this endpoint that touches `Session`/commits anything).

**Non-Goals:**
- Not persisting conversations - see proposal.md.
- Not assigning or creating categories - see proposal.md.
- Not building a generic/reusable "LLM tool-calling framework" - five hardcoded tool definitions matching five hardcoded schemas is the right size for this.
- Not supporting editing/deleting existing entities via chat - creation only, matching the two examples that motivated this feature.

## Decisions

**Response is a discriminated union.** `POST /agent/chat` returns one of:
```jsonc
// type: "proposed_action"
{ "type": "proposed_action", "entity": "gasto", "fields": { "monto": "50000", "fecha": "2026-08-19", "descripcion": "gasolina" } }
// type: "clarification_needed"
{ "type": "clarification_needed", "message": "¿Cuánto le abonaste a Juan?" }
// type: "reply"
{ "type": "reply", "message": "Puedo ayudarte a registrar gastos, deudas, tareas y más - ¿qué necesitas registrar?" }
```
`entity` is one of `gasto | concepto | tarea | deudor | abono`; `fields` matches that entity's `*Create` schema (minus `categoria_ids`). This is the exact contract the sibling frontend change consumes - keep it stable once implemented, since breaking it breaks that change independently.
*Alternative considered*: always return free text and have the frontend re-parse it. Rejected - defeats the purpose of structured tool-calling, which already gives typed arguments.

**Request carries full history + client date, no server session.** Request body: `{ "messages": [{ "role": "user" | "model", "content": "..." }, ...], "current_date": "2026-08-19" }`. `current_date` comes from the browser (`new Date()` client-side), not the server clock, since the server doesn't know the user's timezone - it's injected into the system prompt so "hoy"/"ayer" resolve correctly, mirroring how `Header`/date-sensitive UI already treat "today" as a client-local concept in the frontend rather than something the backend computes.

**Tool execution is pure data-shaping, no DB writes except the one necessary read.** The five tool "handlers" in `agent_service.py` do not call any `*_service.py` creation function. `crear_gasto`/`crear_concepto`/`crear_tarea`/`crear_deudor` handlers just validate/pass through the model's extracted arguments into the response shape above. Only `crear_abono`'s handler touches the database, and only with a read (`SELECT` on `Deudor` filtered by `user_id` and a case-insensitive name match) to resolve the name-to-id mapping described in the spec - never a write.

**Debtor name matching**: case-insensitive substring match against the user's active `Deudor.nombre` values (mirrors no existing precedent in this codebase for fuzzy matching, so keep it simple: `ilike` on Postgres, equivalent SQLModel filter). Zero matches or 2+ matches both produce `clarification_needed`, per the spec.

**System prompt owns the "ask if missing" behavior**, not application code checking for `None` fields after the fact. The five tool schemas mark their genuinely-required fields as required (per each `*Create` schema's own required/optional split - e.g. `Gasto.descripcion` is required, `Concepto.dia_vencimiento` is optional), and the system prompt instructs the model to ask a follow-up question in plain text instead of calling a tool with incomplete information, rather than calling it with nulls/placeholders. This is standard Gemini function-calling practice (the model is capable of choosing not to call a tool and responding with text instead) rather than a custom validation layer.

**Error handling**: wrap the Gemini API call in a try/except; on any failure (network, timeout, API error), return an HTTP 502 with a distinct error body - never let it surface as a malformed `reply`/`proposed_action`/`clarification_needed`, so the frontend can show a "something went wrong, try again" state distinctly from a normal conversational turn.

**Rate limiting**: reuse `app/services/rate_limit.py`'s existing in-memory limiter, keyed by user id (not IP, since this endpoint is always authenticated, unlike the pre-auth `/auth/*` endpoints it was originally built for) - same module, new key namespace, no new dependency.

## Risks / Trade-offs

[In-memory rate limiting resets on every backend restart/redeploy, same as the existing auth endpoints' limiter] → Accepted - matches existing behavior/precedent in this codebase, not a new risk introduced here.
[Gemini's tool-calling reliability for ambiguous Spanish input (the user's primary language) hasn't been empirically verified in this codebase] → Mitigate by writing the system prompt and a handful of manual test messages (see tasks.md) explicitly in Spanish during implementation, not just assuming English-tuned examples generalize.
[`google-genai` is a new external dependency and a new paid API surface] → Scoped tightly (one service file, one router, one schema file) so it's easy to remove entirely if it doesn't pan out, without touching any existing entity's code path.
