## MODIFIED Requirements

### Requirement: View current preferences
The system SHALL let an authenticated user retrieve their own profile, including their currently selected accent color (or its absence, meaning the app default applies) and their computed `ahorros` savings balance, which is always present (defaulting to zero) since it is now sourced from their savings ledger rather than a manually-set value.

#### Scenario: User has chosen an accent color
- **WHEN** an authenticated user requests their profile and has previously set an accent color
- **THEN** the system returns that color's identifier

#### Scenario: User has not chosen an accent color
- **WHEN** an authenticated user requests their profile and has never set an accent color
- **THEN** the system returns no color identifier, meaning the app's default applies

#### Scenario: User has set a savings figure
- **WHEN** an authenticated user requests their profile and has recorded one or more savings ledger entries
- **THEN** the system returns their computed running balance

#### Scenario: User has not configured Disponible tracking
- **WHEN** an authenticated user requests their profile
- **THEN** the response contains no Disponible-related fields at all, since Disponible tracking no longer exists as a feature

### Requirement: Preferences are scoped to the authenticated user
The system SHALL ensure a user can only view or modify their own preferences, never another user's.

#### Scenario: Requests always act on the authenticated user
- **WHEN** an authenticated user views or updates preferences
- **THEN** the system only ever reads or writes that same user's own record, regardless of any other identifier

## REMOVED Requirements

### Requirement: Set or clear the savings figure
**Reason**: Superseded by the `savings-tracking` capability's ledger — `ahorros` is no longer a single value a user directly sets or clears, it is computed from their recorded contributions and withdrawals.
**Migration**: A user's existing non-null `ahorros` value becomes the first entry in their savings ledger (see `savings-tracking`); going forward, they record contributions and withdrawals through that capability's endpoints instead of `PATCH /users/me`.
