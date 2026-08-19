## Purpose

Lets an authenticated user describe a financial action in plain language (a Gasto, Concepto, Tarea, Deudor, or Abono) and get back a structured, ready-to-review proposal instead of having to fill out a form - without the system ever writing that action to the database on its own.

## ADDED Requirements

### Requirement: Chat endpoint requires authentication
The system SHALL require a valid JWT for every request to the agent chat endpoint, identical to every other authenticated endpoint, and SHALL scope every tool call to the authenticated user's own data.

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request to the chat endpoint carries no valid JWT
- **THEN** the system responds 401, the same as any other protected endpoint

#### Scenario: Tools never see another user's data
- **WHEN** the model calls a tool that needs to look up existing data (e.g. resolving a debtor's name for `crear_abono`)
- **THEN** the lookup is scoped to the authenticated user's own records only

### Requirement: Conversation is stateless
The system SHALL NOT persist chat messages or conversation state server-side. Each request SHALL carry the full message history needed to interpret the latest message, supplied by the caller.

#### Scenario: Server restart loses no user-visible state
- **WHEN** the backend process restarts between two messages of the same conversation
- **THEN** the conversation continues normally as long as the caller still sends the full history with its next request - nothing was expected to survive server-side

### Requirement: A recognized action is proposed, never executed
The system SHALL NOT create, update, or delete any Gasto, Concepto, Tarea, Deudor, or Abono as a result of a chat message. When the model determines the message maps to one of the five supported actions with all required fields present, the system SHALL return a structured proposed action (entity type and extracted fields) instead of executing it.

#### Scenario: A complete message produces a proposal, not a write
- **WHEN** the user's message contains everything required for one of the five supported actions (e.g. "Hoy gasté 50.000 en gasolina" has enough for a Gasto)
- **THEN** the response is a proposed action with the extracted fields, and no row is created in any table

#### Scenario: Proposal fields map to the real creation schema
- **WHEN** a proposed action is returned for a given entity type
- **THEN** its fields correspond one-to-one with that entity's existing creation fields (minus category assignment, out of scope for this capability), so the caller can submit them to the existing creation endpoint unchanged

### Requirement: Missing required fields trigger a clarifying question
The system SHALL respond with a clarifying question, not a proposed action, when the model determines a required field for the matched entity type is missing from the conversation so far.

#### Scenario: An incomplete message asks instead of guessing
- **WHEN** the user's message matches an entity type but omits a value that entity type requires (e.g. a debt's amount without its interest rate is fine, since amortization terms are optional, but a debtor's name without an amount is not)
- **THEN** the response is a clarifying question naming what's missing, not a proposed action with a guessed or empty value

### Requirement: Debtor name resolution for abonos
When the model calls the abono tool, the system SHALL resolve the debtor name it received against the authenticated user's own debtors before returning a proposed action, rather than trusting an id supplied by the model.

#### Scenario: Exactly one matching debtor
- **WHEN** the abono tool's debtor name matches exactly one of the user's debtors
- **THEN** the proposed action includes that debtor's real id

#### Scenario: No matching debtor
- **WHEN** the abono tool's debtor name matches none of the user's debtors
- **THEN** the system returns a clarifying question about the debtor instead of a proposed action, rather than inventing or guessing an id

#### Scenario: Multiple matching debtors
- **WHEN** the abono tool's debtor name matches more than one of the user's debtors
- **THEN** the system returns a clarifying question listing the ambiguous matches instead of picking one

### Requirement: Out-of-scope messages are handled gracefully
The system SHALL return a plain conversational response, neither a proposed action nor an error, when the user's message doesn't map to any of the five supported entity types.

#### Scenario: Unrelated message
- **WHEN** the user sends a message unrelated to any supported action (e.g. a general question)
- **THEN** the system responds conversationally without proposing an action or raising an error

### Requirement: Upstream failures are surfaced, not swallowed
The system SHALL return a clear error response, distinguishable from a clarifying question or a proposed action, when the Gemini API call fails, times out, or is unavailable.

#### Scenario: Gemini API is unreachable
- **WHEN** the call to the Gemini API fails or times out
- **THEN** the endpoint returns an error response the caller can distinguish from a normal chat reply, instead of hanging or returning a malformed proposal

### Requirement: Chat messages are rate-limited
The system SHALL rate-limit the chat endpoint per user, using the same in-memory approach already applied to `/auth/register` and `/auth/login`, since each message triggers a paid external API call.

#### Scenario: Excessive messages are throttled
- **WHEN** a user sends chat messages beyond the configured rate limit in the configured window
- **THEN** further requests are rejected until the window resets, the same behavior already in place for the auth endpoints
