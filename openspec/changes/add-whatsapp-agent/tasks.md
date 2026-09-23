## 1. Config and dependency

- [x] 1.1 Add the `twilio` package to `requirements.txt`.
- [x] 1.2 In `app/config.py`, add optional `twilio_account_sid`, `twilio_auth_token`, `twilio_whatsapp_number` settings (mirror `gemini_api_key`'s optionality — the rest of the app must keep working unconfigured).

## 2. Data model

- [x] 2.1 In `app/models/user.py`, add `whatsapp_phone: str | None` (unique, index) and `whatsapp_link_token: str | None` (unique, index) to `User`.
- [x] 2.2 Add `app/models/whatsapp_session.py`: `WhatsAppSession { phone_number: str (primary key), pending_response_json: str | None, pending_original_message: str | None, expires_at: datetime | None }`.
- [x] 2.3 Register the new model in `app/models/__init__.py`. Generate and apply the Alembic migration.

## 3. Agent core extensions (benefit both channels)

- [x] 3.1 In `app/services/agent_service.py`, add `duracion_meses` (optional integer) to the `crear_concepto` tool's `parameters_json_schema`, and mention in the system prompt that a clearly one-time gasto_fijo/ingreso should set it to 1 while an ongoing one should omit it.
- [x] 3.2 Extend `agent_service.chat()` with an optional `audio: tuple[bytes, str] | None` parameter (bytes, mime type); when given, add it as an additional `types.Part` on the current turn's content alongside the existing text-based `Content` construction. Existing callers (the in-app widget via `POST /agent/chat`) are unaffected since they never pass it.

## 4. WhatsApp service

- [x] 4.1 Add `app/services/whatsapp_service.py`:
  - `generate_link_token(session, user) -> str`: regenerates and stores `whatsapp_link_token`, returns it.
  - `resolve_link(session, phone_number, message_body) -> User | None`: if `message_body` matches a live `whatsapp_link_token`, links `phone_number` to that user (sets `whatsapp_phone`, clears the token) and returns the user; otherwise `None`.
  - `get_user_by_phone(session, phone_number) -> User | None`.
  - `handle_incoming(session, phone_number, text: str | None, audio: tuple[bytes, str] | None) -> str`: the orchestrator described in design.md — unlinked-number handling, pending-turn resolution (confirmation keyword match / clarification continuation / expiry), calling `agent_service.chat()` for anything new, mapping a confirmed proposal to the matching `*_service.create_*` call, and upserting/clearing `WhatsAppSession`. Returns the reply text to send back.
- [x] 4.2 Implement the entity → creation-function mapping for `gasto` and `concepto` (v1 scope) inside `whatsapp_service.py`, reusing `gasto_service.create_gasto` / `concept_service.create_concepto` unchanged.
- [x] 4.3 Implement the affirmative/negative keyword matcher (case/accent-insensitive) as a small helper, per design.md's fixed token list.

## 5. Router

- [x] 5.1 Add `app/routers/whatsapp.py`:
  - `POST /whatsapp/webhook`: verifies the Twilio signature (`twilio.request_validator.RequestValidator`) against the full request URL and form body before anything else; parses `From`, `Body`, `NumMedia`/`MediaUrl0`/`MediaContentType0`; downloads audio via Twilio Basic Auth when present; rate-limits by phone number (`check_rate_limit(..., identifier=phone_number)`); calls `whatsapp_service.handle_incoming`; responds with TwiML containing the reply text.
  - `POST /whatsapp/link` (JWT-required): calls `generate_link_token`, returns the token and the fully-formed `wa.me` URL.
  - `DELETE /whatsapp/link` (JWT-required): clears `whatsapp_phone` on the current user.
- [x] 5.2 Register the router in `app/main.py`.

## 6. Tests

- [x] 6.1 Linking: token generation, successful link on matching message, no link on non-matching message from an unlinked number, token single-use (second attempt with the same token fails).
- [x] 6.2 Proposal + confirmation: a complete gasto/concepto message proposes without writing; an affirmative reply creates the row and clears the pending turn; a negative reply discards without creating; an unrecognized reply discards and is itself processed as a new message.
- [x] 6.3 Clarification continuation: an incomplete message asks a clarifying question; the next message is correctly interpreted together with the original message and the question.
- [x] 6.4 Expiry: a reply more than 20 minutes after a pending turn was set is treated as a new message, not matched against it.
- [x] 6.5 `duracion_meses`: a one-time-sounding concepto message proposes `duracion_meses=1`; an ongoing-sounding one omits it. (Direct test against `agent_service.chat()`, exercises both the in-app and WhatsApp paths identically.)
- [x] 6.6 Webhook signature verification: an unsigned/mismatched request is rejected before any processing.
- [x] 6.7 Rate limiting: excessive messages from one phone number are throttled independently of any other number.
- [x] 6.8 Run the full backend test suite and confirm everything passes.

## 7. Manual verification (Twilio sandbox)

- [x] 7.1 Configure a Twilio account, WhatsApp sandbox number, and the new env vars locally.
- [ ] 7.2 End-to-end: link a real phone number via the generated wa.me link, send a text gasto, confirm it, verify it appears in the app; send an ambiguous one, verify the clarifying question and a correct follow-up; send a voice note, verify it's understood.
