## MODIFIED Requirements

### Requirement: View current preferences
The system SHALL let an authenticated user retrieve their own profile, including their currently selected accent color (or its absence, meaning the app default applies), their `ahorros` savings figure (or its absence, meaning it has never been set), and their Disponible baseline (`saldo_disponible_inicial` and `saldo_disponible_fecha`, or their absence, meaning Disponible tracking has never been configured).

#### Scenario: User has chosen an accent color
- **WHEN** an authenticated user requests their profile and has previously set an accent color
- **THEN** the system returns that color's identifier

#### Scenario: User has not chosen an accent color
- **WHEN** an authenticated user requests their profile and has never set an accent color
- **THEN** the system returns no color identifier, meaning the app's default applies

#### Scenario: User has set a savings figure
- **WHEN** an authenticated user requests their profile and has previously set `ahorros`
- **THEN** the system returns that value

#### Scenario: User has not configured Disponible tracking
- **WHEN** an authenticated user requests their profile and has never set `saldo_disponible_inicial`
- **THEN** the system returns no value for `saldo_disponible_inicial` or `saldo_disponible_fecha`

### Requirement: Preferences are scoped to the authenticated user
The system SHALL ensure a user can only view or modify their own preferences, including `ahorros` and the Disponible baseline, never another user's.

#### Scenario: Requests always act on the authenticated user
- **WHEN** an authenticated user views or updates preferences
- **THEN** the system only ever reads or writes that same user's own record, regardless of any other identifier

## ADDED Requirements

### Requirement: Set or clear the savings figure
The system SHALL let an authenticated user set their `ahorros` figure to any value, or clear it back to unset, with no validation beyond it being a valid amount.

#### Scenario: Setting a savings figure
- **WHEN** a user sets `ahorros` to a value
- **THEN** the system saves it and subsequent profile reads return it

#### Scenario: Clearing the savings figure
- **WHEN** a user who previously set `ahorros` clears it
- **THEN** subsequent profile reads report no value for `ahorros`

### Requirement: Setting the Disponible baseline always re-dates it to today
The system SHALL, whenever a user sets `saldo_disponible_inicial` to a new value, record `saldo_disponible_fecha` as the current server date, regardless of any date supplied by the client.

#### Scenario: First-time setup
- **WHEN** a user sets `saldo_disponible_inicial` for the first time
- **THEN** the system saves that value with today's date as `saldo_disponible_fecha`

#### Scenario: Re-baselining an existing value
- **WHEN** a user who previously set `saldo_disponible_inicial` sets it again to a new value
- **THEN** the system replaces both the value and `saldo_disponible_fecha` with today's date, discarding the previous baseline date
