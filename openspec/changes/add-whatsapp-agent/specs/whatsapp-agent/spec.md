## ADDED Requirements

### Requirement: Inbound webhook requests are verified
The system SHALL reject any request to the WhatsApp webhook whose Twilio signature does not validate against the configured auth token and the request's full URL and body.

#### Scenario: Unsigned or mismatched request is rejected
- **WHEN** a request to the webhook arrives without a valid `X-Twilio-Signature` header
- **THEN** the system rejects it and performs no further processing

### Requirement: A phone number must be linked to a TOBE account before use
The system SHALL let an authenticated user generate a one-time linking token and a WhatsApp deep link containing it. The system SHALL link a phone number to that user's account the first time a message from that number matches a live, unexpired linking token, consuming the token so it cannot be reused. The system SHALL NOT process any other message content from a phone number that has no linked account.

#### Scenario: Generating a link token
- **WHEN** an authenticated user requests a WhatsApp link
- **THEN** the system returns a deep link containing a fresh one-time token tied to that user

#### Scenario: First message from the deep link links the number
- **WHEN** a message arrives whose body matches a live linking token
- **THEN** the sending phone number becomes linked to the token's user, and the token can no longer be used

#### Scenario: Unlinked number sending anything else
- **WHEN** a message arrives from a phone number with no linked account and a body that doesn't match any live linking token
- **THEN** the system replies with instructions to link via the app, without calling the AI agent

### Requirement: A recognized action is proposed by text, then confirmed by text
The system SHALL, for a linked number's message with enough information for a supported action (gasto or concepto), reply with a human-readable description of the proposed action and store it as that phone number's single pending turn, without creating anything yet. The system SHALL execute the pending action only when the next message from that number is a recognized affirmative reply, and SHALL discard it without executing on a recognized negative reply.

#### Scenario: A complete message produces a proposal, not a write
- **WHEN** a linked number sends a message with enough information for a gasto or concepto
- **THEN** the reply describes the proposed action and asks for confirmation, and no row is created yet

#### Scenario: An affirmative reply executes the pending action
- **WHEN** the next message from that number is a recognized affirmative reply
- **THEN** the pending action is created via the same logic the app's own creation endpoints use, and the pending turn is cleared

#### Scenario: A negative reply discards the pending action
- **WHEN** the next message from that number is a recognized negative reply
- **THEN** the pending action is discarded without being created, and the pending turn is cleared

#### Scenario: An unrecognized reply discards the pending action and starts fresh
- **WHEN** the next message from that number is neither a recognized affirmative nor negative reply
- **THEN** the pending action is discarded silently, and the new message is processed as a new request

### Requirement: A missing required field is asked for, and the answer is understood in context
The system SHALL, when the agent determines a required field is missing, reply with the clarifying question and store enough of the exchange as that phone number's pending turn to interpret the next message as an answer to it, rather than a message in isolation.

#### Scenario: A clarifying question is followed up correctly
- **WHEN** a linked number's message is missing a required field and a clarifying reply is sent
- **THEN** the next message from that number is interpreted together with the original message and the clarifying question, not on its own

### Requirement: A pending turn expires
The system SHALL discard a phone number's pending turn if no reply arrives within 20 minutes, so a much later, unrelated message is never matched against a stale proposal or clarification.

#### Scenario: A late reply is treated as a new message
- **WHEN** a reply arrives more than 20 minutes after its proposal or clarifying question was sent
- **THEN** the reply is processed as a new message, not matched against the expired pending turn

### Requirement: A voice note is understood the same as a typed message
The system SHALL, for a voice note from a linked number, extract the same kind of action from its audio content as it would from equivalent typed text, without requiring the sender to type anything.

#### Scenario: A voice note produces a proposal
- **WHEN** a linked number sends a voice note describing a gasto or concepto
- **THEN** the reply describes a proposed action extracted from the audio, following the same proposal-then-confirm flow as a typed message

### Requirement: WhatsApp messages are rate-limited per phone number
The system SHALL throttle inbound messages per sending phone number, independently of any user-id-based limiting, since WhatsApp requests carry no authenticated user id.

#### Scenario: Excessive messages from one number are throttled
- **WHEN** a single phone number sends messages far more frequently than normal use would require
- **THEN** further messages from that number are rejected until the window resets
