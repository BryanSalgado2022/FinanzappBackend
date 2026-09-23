## Context

See proposal.md for motivation and the grilled decisions behind each choice below. This builds on the already-shipped `agent-chat` capability (`app/services/agent_service.py`'s `chat()`, `app/schemas/agent.py`'s response types) rather than duplicating it — WhatsApp is a second caller of the same extraction logic, not a parallel implementation.

## Goals / Non-Goals

**Goals:**
- Let a linked WhatsApp number send a text or voice message and have it become a confirmed Gasto/Concepto through the existing agent, with the same never-write-without-confirmation guarantee the in-app widget already has.
- Keep server-side state to the minimum needed to resolve one pending turn per phone number.

**Non-Goals:**
- Full conversation history over WhatsApp (out of scope, per the same statelessness principle `agent-chat` already has — just applied differently, since WhatsApp can't resend history like a web client can).
- The frontend linking UI (sibling change, `add-whatsapp-agent-ui`).
- Deudor/tarea/abono actions over WhatsApp (v1 is gasto + concepto only; the same tools already exist for the in-app widget, extending WhatsApp to the rest is a later, smaller change once this is proven).
- Auto-executing without confirmation, at any amount threshold.

## Decisions

### Twilio, not Meta Cloud API directly
Grilled and chosen for time-to-first-working-test: Twilio's sandbox works today with no Meta Business Manager verification. Twilio also hands back media as a directly-downloadable authenticated URL (Basic Auth with the account SID/auth token) rather than Meta's two-step media-id-then-media-url flow, which simplifies voice note handling specifically.

### Linking: wa.me deep link with a prefilled one-time token
Mirrors the existing `User.ics_token` pattern (a regenerable secret identifying the user to an otherwise-unauthenticated flow) almost exactly. `POST /whatsapp/link` (JWT-required) generates a random token, stores it on `whatsapp_link_token`, and returns `https://wa.me/<twilio_number>?text=<url-encoded token>`. The frontend opens that link; the user just taps send. The webhook, on receiving a message from an unlinked phone number, checks whether the message body matches a live `whatsapp_link_token` — if so, links the number and clears the token (single use); otherwise replies with instructions to link via the app. No manual code entry, no credentials over chat.

### Pending-turn state: one row per phone number, not a growing log
`WhatsAppSession(phone_number PK, pending_response_json, pending_original_message, expires_at)`. `pending_response_json` is the serialized `ProposedActionResponse` or `ClarificationNeededResponse` (the same Pydantic types `agent-chat` already returns — reused, not redefined) tagged by its own `type` field so the reader knows which. `pending_original_message` is only populated for a clarification, since resuming it means re-calling `agent_service.chat()` with a small reconstructed 2-3 message context (`[user: original_message, model: clarification_question, user: new_reply]`) — the *only* place anything resembling "history" is reconstructed, and only ever 2-3 messages, never accumulated. `expires_at` is set to 20 minutes out on every write; an expired or absent row means "treat the incoming message as brand new." A row is UPSERTed (`INSERT ... ON CONFLICT (phone_number) DO UPDATE`), never appended to, matching the "only the pending turn" decision — there is never more than one row per phone number.

### Reply interpretation: simple keyword match first, no Gemini round-trip for yes/no
A pending `ProposedActionResponse` reply is checked against a small fixed set of affirmative (`sí`, `si`, `dale`, `confirmar`, `ok`, `1`) and negative (`no`, `cancelar`, `2`) tokens, case/accent-insensitive. A match executes or discards immediately, no LLM call. Anything else discards the pending row silently and falls through to treating the message as brand new — this was the explicitly grilled choice over re-consulting Gemini on every reply, trading a small amount of flexibility (an ambiguous reply like "mejor no, era de ayer" won't be understood as a correction) for predictability and one fewer Gemini call per confirmation.

### Confirmed actions execute via the same service functions the REST layer calls
`whatsapp_service.py` maps `entity → service function` exactly like `AgentProposedActionCard.tsx`'s "Confirmar" maps `entity → useCreate*` hook, just server-side: `gasto` → `gasto_service.create_gasto`, `concepto` → `concept_service.create_concepto`, and so on for the entities in scope for v1. No new creation logic anywhere — this is purely a new caller of functions that already exist and are already tested.

### Audio: one multimodal Gemini call, no separate transcription step
Twilio's inbound webhook includes `NumMedia`/`MediaUrl0`/`MediaContentType0` for a voice note. The webhook downloads the audio (Basic Auth, Twilio credentials) and passes it straight into `agent_service.chat()` as an additional `types.Part` on the current turn, alongside — not instead of — the existing text-message flow (a message is either text or audio, never both, for v1). Gemini's tool-calling and audio understanding happen in the same call, so extraction quality depends on Gemini's audio comprehension directly rather than an intermediate transcript that could itself introduce errors. `chat()`'s signature grows an optional `audio: tuple[bytes, str] | None` (bytes, mime type) parameter; the in-app widget never passes it, so this is additive and doesn't touch the existing text-only path.

### `duracion_meses` added to the `crear_concepto` tool
Already a real, fully-supported `Concepto` field (`app/schemas/concepto.py`, `app/services/entry_service.py`'s `generar_entradas_recurrentes`) for `gasto_fijo`/`ingreso` only — generates exactly that many consecutive months and stops. The tool schema simply didn't expose it, so neither channel's agent could set it. Adding it to `TOOLS` in `agent_service.py` is additive to the existing `agent-chat` capability and benefits the in-app widget too, not WhatsApp-specific — hence the `MODIFIED` delta against `agent-chat`'s existing requirement rather than something scoped only to `whatsapp-agent`.

### Timezone: fixed to `America/Bogota`
No client to compute "today" for a WhatsApp message the way the web app's `current_date` field does. Every webhook-driven `chat()` call resolves "today" from the server clock converted to `America/Bogota`, hardcoded — not a new per-user timezone field, since there's no signal today that TOBE has or will have non-Colombia users.

### Unlinked number: reply with instructions, no Gemini call
Checked before anything else in the webhook handler — if the phone number isn't linked and the message body isn't a valid pending link token, reply with a fixed instructional message and stop. Never spend a Gemini call on a message from a number that can't do anything useful yet.

### Webhook security
Every inbound request is verified with Twilio's `RequestValidator` (`X-Twilio-Signature` header against the full request URL + form body, using `twilio_auth_token`) before any processing — an unsigned or mismatched request is rejected outright. This is the direct analog of every other endpoint's JWT check; a WhatsApp channel has no JWT, so the signature is what stands in for "this request is really who it claims to be."

## Risks / Trade-offs

- **New native SQL storage pattern** (`pending_response_json`, `pending_original_message` as plain `str` columns holding JSON-serialized Pydantic output) rather than a typed JSON column — deliberate: this codebase has no existing JSON column precedent, and this state is small, short-lived, and never queried structurally (only ever read back whole by phone number), so a typed JSON column would add a new pattern without a matching benefit.
- **Twilio webhook timeout**: the webhook responds synchronously with TwiML after the full Gemini round-trip (and, for audio, a download-then-Gemini round-trip). If this proves slow enough to risk Twilio's own webhook timeout under real usage, the fix is to ack immediately and send the reply via Twilio's REST API asynchronously instead — deferred until it's observed to actually be a problem, not built preemptively.
- **In-memory rate limiting** (`app/services/rate_limit.py`) is explicitly single-process only (see its own comment, and `add-password-auth`'s design.md) — unaffected by this change, just reused with a phone-number key instead of a user-id key, inheriting the same known limitation.
