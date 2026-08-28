## MODIFIED Requirements

### Requirement: View current preferences
The system SHALL let an authenticated user retrieve their own profile, including their currently selected accent color (or its absence, meaning the app default applies) and their `ahorros` savings figure (or its absence, meaning it has never been set).

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
- **WHEN** an authenticated user requests their profile
- **THEN** the response contains no Disponible-related fields at all, since Disponible tracking no longer exists as a feature

### Requirement: Preferences are scoped to the authenticated user
The system SHALL ensure a user can only view or modify their own preferences, including `ahorros`, never another user's.

#### Scenario: Requests always act on the authenticated user
- **WHEN** an authenticated user views or updates preferences
- **THEN** the system only ever reads or writes that same user's own record, regardless of any other identifier

## REMOVED Requirements

### Requirement: Setting the Disponible baseline always re-dates it to today
**Reason**: The Disponible feature (`available-balance` capability) is removed after user testing found it confusing.
**Migration**: None. `saldo_disponible_inicial`/`saldo_disponible_fecha` are dropped; `ahorros` is unaffected and keeps its own independent set/clear behavior.
