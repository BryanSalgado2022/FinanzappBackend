## Purpose
Lets a user see their TOBE payment dates and other Agenda events in Google Calendar, their phone's calendar, or any other tool, via the standard iCalendar (.ics) format, without TOBE integrating with each calendar provider individually.

## ADDED Requirements

### Requirement: Authenticated calendar download
The system SHALL let an authenticated user download an `.ics` file of their own events via `GET /calendar/export`.

#### Scenario: Downloading the calendar
- **WHEN** an authenticated user requests `GET /calendar/export`
- **THEN** the system returns a valid `.ics` file containing that user's events

#### Scenario: Requests are scoped to the authenticated user
- **WHEN** an authenticated user downloads their calendar
- **THEN** it contains only that user's own events, never another user's

### Requirement: Event coverage matches the in-app Agenda
The system SHALL include, in the generated calendar, the same categories of dated events already shown in the in-app Agenda: concept due dates, debt payoff celebrations, variable expenses, tasks, debtor start dates, abonos, and debtor payoff dates.

#### Scenario: Concept due dates are included
- **WHEN** the user has a concept with a due day and a monthly entry in the covered range
- **THEN** the calendar includes an event on that entry's due date

#### Scenario: Variable expenses, tasks, and debtor activity are included
- **WHEN** the user has a variable expense, task, debtor start date, abono, or debtor payoff date in the covered range
- **THEN** the calendar includes a corresponding event

### Requirement: Calendar covers a rolling window around today
The system SHALL include only events dated from 3 months before today through 12 months after today, computed at request time.

#### Scenario: Events outside the window are excluded
- **WHEN** the user has events dated more than 3 months in the past or more than 12 months in the future
- **THEN** the calendar does not include them

#### Scenario: The window moves with time
- **WHEN** the calendar is requested again later (e.g. via a subscribed calendar app polling it)
- **THEN** the included window shifts forward accordingly, since it's always relative to the current date at request time

### Requirement: Token-based subscription
The system SHALL let an authenticated user generate a secret token via `POST /calendar/token`, view their current token (if any) via `GET /calendar/token` without changing it, and SHALL serve the same `.ics` content, without requiring authentication, at `GET /calendar/subscribe/{token}` for a valid token.

#### Scenario: Generating a token for the first time
- **WHEN** an authenticated user with no existing token requests `POST /calendar/token`
- **THEN** the system creates and returns a new secret token

#### Scenario: Viewing the current token without regenerating
- **WHEN** an authenticated user requests `GET /calendar/token`
- **THEN** the system returns their existing token unchanged, or none if they've never generated one, without invalidating anything

#### Scenario: Subscribing with a valid token
- **WHEN** a request is made to `GET /calendar/subscribe/{token}` with a token that belongs to a user
- **THEN** the system returns that user's `.ics` calendar without requiring a login

#### Scenario: Invalid token is rejected
- **WHEN** a request is made to `GET /calendar/subscribe/{token}` with a token that doesn't match any user
- **THEN** the system responds with an error, not another user's calendar

### Requirement: Regenerating the token invalidates the previous one
The system SHALL, when an authenticated user requests `POST /calendar/token` again, replace their existing token with a new one, invalidating the old one.

#### Scenario: Regenerating replaces the old token
- **WHEN** a user who already has a token requests a new one
- **THEN** the old token no longer works at `GET /calendar/subscribe/{token}`, and only the newly issued token does
