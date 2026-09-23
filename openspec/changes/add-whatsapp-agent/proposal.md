## Why

The user wants to send expenses/income to TOBE by WhatsApp message (text or voice note) and have the existing AI agent interpret and register them, instead of opening the app. The agent's extraction logic (`agent_service.chat()`) already exists and is channel-agnostic — it takes messages and a user, returns a proposal — but today it's only reachable from the in-app widget via an authenticated JWT request with the full conversation resent each turn. WhatsApp has no JWT and is driven by webhooks, so this change adds a second channel on top of the same agent core, grilled and scoped this session:

- Twilio for the WhatsApp API (not Meta Cloud API directly — faster to a working sandbox, no upfront Business Manager verification).
- Linking a phone number to a TOBE account via a one-tap deep link (`wa.me` with a prefilled token), not a manually-typed code or credentials over chat.
- The agent still never writes directly — WhatsApp gets the same "propose, then confirm" principle as the in-app widget, translated to a text reply ("sí"/"no") instead of a button click.
- Minimal server-side state: only the single pending turn per phone number (a proposal awaiting confirmation, or a clarification awaiting an answer), with a short expiry — not a resent conversation history like the widget.
- Voice notes are supported in v1 (very common in Colombia) via Gemini's native audio understanding, not a separate transcription step.

## What Changes

- New Twilio webhook (`POST /whatsapp/webhook`) receives inbound WhatsApp messages (text or audio), resolves the sending phone number to a TOBE user, and drives the same agent extraction logic used today.
- New linking flow: an authenticated endpoint generates a one-time token and the wa.me URL; the user's first WhatsApp message (the prefilled token) links their number to their account.
- New minimal per-phone-number pending-turn state (a single row, not history) so a "sí"/"no" reply or a clarification's answer can be resolved without resending context.
- On confirmation, the proposed action is executed directly by calling the same service-layer creation functions the REST endpoints already use (`gasto_service.create_gasto`, `concept_service.create_concepto`, etc.) — no new business logic, just a new caller.
- `agent_service`'s `crear_concepto` tool gains `duracion_meses`, so the model can distinguish a one-time income/expense (`duracion_meses=1`) from an ongoing one (omitted) from the wording of the message alone — this already existed as a `Concepto` field and already works for the in-app widget once exposed, it just wasn't in the tool schema yet.
- `agent_service.chat()` gains optional audio input (inline `Part`, no separate transcription call) so a voice note is understood in the same request that extracts the action.
- Rate limiting mirrors the existing chat endpoint's, keyed by phone number instead of user id (WhatsApp has no JWT to key by).
- Not in this change: the small frontend "Conectar WhatsApp" button/screen — a sibling `add-whatsapp-agent-ui` change follows once this is working end-to-end.

## Capabilities

### New Capabilities
- `whatsapp-agent`: receiving, interpreting, and confirming financial actions sent via WhatsApp (text or voice), linked to a TOBE account.

### Modified Capabilities
- `agent-chat`: the `crear_concepto` tool gains `duracion_meses`, letting the model express a one-time vs. ongoing income/expense.

## Impact

- `app/models/user.py`: `User` gains `whatsapp_phone: str | None` (unique, linked number) and `whatsapp_link_token: str | None` (unique, transient linking secret) — mirrors the existing `ics_token` pattern.
- New `app/models/whatsapp_session.py`: `WhatsAppSession` (one row per phone number) holding the single pending turn (serialized proposal or clarification + expiry).
- New Alembic migration for both.
- New `app/services/whatsapp_service.py`: linking, incoming-message orchestration, pending-turn resolution, execution-on-confirm.
- New `app/routers/whatsapp.py`: `POST /whatsapp/webhook` (Twilio-facing, signature-verified), `POST /whatsapp/link` (JWT-authenticated, generates the link token + wa.me URL), `DELETE /whatsapp/link` (unlink).
- `app/services/agent_service.py`: `crear_concepto` tool schema gains `duracion_meses`; `chat()` gains optional audio input.
- `app/config.py`: new `twilio_account_sid`, `twilio_auth_token`, `twilio_whatsapp_number` settings (optional, like `gemini_api_key` — the rest of the app must keep working when unconfigured).
- New dependency: `twilio` Python SDK (signature verification + sending replies).
