## 1. Setup

- [x] 1.1 Add `google-genai` to `requirements.txt` (verify current stable version)
- [x] 1.2 Add `gemini_api_key: str` to `Settings` in `app/config.py`
- [x] 1.3 Add `GEMINI_API_KEY` to `.env.example` with a comment explaining it's for the AI chat agent

## 2. Schemas

- [x] 2.1 `app/schemas/agent.py`: `ChatMessage` (role, content), `ChatRequest` (messages, current_date), and the discriminated response union (`ProposedActionResponse`, `ClarificationNeededResponse`, `ReplyResponse`) per design.md's exact shape

## 3. Tool definitions and service

- [x] 3.1 `app/services/agent_service.py`: define the five tool schemas (crear_gasto, crear_concepto, crear_tarea, crear_deudor, crear_abono) mapped field-for-field to `GastoCreate`/`ConceptoCreate`/`TareaCreate`/`DeudorCreate`/`AbonoCreate` (minus `categoria_ids` everywhere)
- [x] 3.2 System prompt: instructs the model to (a) use `current_date` for relative dates, (b) ask a clarifying text question instead of calling a tool with a missing required field, (c) only call a tool when confident, (d) reply conversationally for anything unrelated to the five entities
- [x] 3.3 Implement the `crear_abono` handler's debtor name resolution (case-insensitive match against the authenticated user's own `Deudor` rows; zero or 2+ matches → clarification_needed)
- [x] 3.4 Implement the main `chat()` service function: call Gemini with the message history + system prompt + tools, branch on the model's response into `proposed_action` / `clarification_needed` / `reply`, wrap the Gemini call in error handling → 502 on failure

## 4. Router

- [x] 4.1 `app/routers/agent.py`: `POST /agent/chat`, requires `get_current_user`, rate-limited per user id via `app/services/rate_limit.py`
- [x] 4.2 Register the router in `app/main.py`

## 5. Tests

- [x] 5.1 Mock the Gemini API call (never hit the real API in tests, matching how Google auth is already mocked in `tests/conftest.py`)
- [x] 5.2 Test: complete message → proposed_action, with fields matching the entity's create schema
- [x] 5.3 Test: incomplete message → clarification_needed
- [x] 5.4 Test: unrelated message → reply
- [x] 5.5 Test: abono with a debtor name that matches exactly one debtor → proposed_action with the resolved id
- [x] 5.6 Test: abono with a debtor name matching zero debtors → clarification_needed
- [x] 5.7 Test: abono with a debtor name matching 2+ debtors → clarification_needed
- [x] 5.8 Test: unauthenticated request → 401
- [x] 5.9 Test: a tool lookup (debtor resolution) never returns another user's data
- [x] 5.10 Test: Gemini API failure → 502 with a distinguishable error body
- [x] 5.11 Test: rate limit trips after the configured threshold, same pattern as the existing auth rate-limit tests
- [x] 5.12 Full suite passes (`pytest`)

## 6. Documentation

- [x] 6.1 README: add `POST /agent/chat` to the endpoints table, and add `GEMINI_API_KEY` to the "Despliegue" section's Railway environment variable table

## 7. Manual verification

- [ ] 7.1 Start the server locally with a real `GEMINI_API_KEY`, send the two example messages from the original request ("Hoy gasté 50.000 en gasolina para el carro", "Debo 250.000.000 por crédito hipotecario a 10 años a una tasa de interés del 1.47%") via curl/httpie, confirm both produce sensible `proposed_action` responses
- [ ] 7.2 Send a deliberately incomplete message (e.g. "Le aboné a Juan"), confirm a clarifying question about the missing amount
- [ ] 7.3 Send an abono message where the named debtor doesn't exist yet, confirm clarification_needed rather than a fabricated id
- [ ] 7.4 Send an unrelated message, confirm a plain reply with no proposed action
