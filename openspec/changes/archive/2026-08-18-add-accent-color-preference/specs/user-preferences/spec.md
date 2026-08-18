## Purpose

Lets an authenticated user view and update account-level preferences that personalize their experience, starting with an accent color choice, so the preference follows their account across devices rather than living only on one browser.

## ADDED Requirements

### Requirement: View current preferences
The system SHALL let an authenticated user retrieve their own profile, including their currently selected accent color (or its absence, meaning the app default applies).

#### Scenario: User has chosen an accent color
- **WHEN** an authenticated user requests their profile and has previously set an accent color
- **THEN** the system returns that color's identifier

#### Scenario: User has not chosen an accent color
- **WHEN** an authenticated user requests their profile and has never set an accent color
- **THEN** the system returns no color identifier, meaning the app's default applies

### Requirement: Set accent color from a curated set
The system SHALL let an authenticated user set their accent color to one of a fixed, curated set of identifiers, and SHALL reject any value outside that set.

#### Scenario: Setting a valid accent color
- **WHEN** a user sets their accent color to one of the allowed identifiers
- **THEN** the system saves it and subsequent profile reads return it

#### Scenario: Rejecting an invalid accent color
- **WHEN** a user attempts to set their accent color to a value outside the allowed set
- **THEN** the system rejects the request without changing the stored preference

### Requirement: Clear accent color back to the default
The system SHALL let an authenticated user clear their accent color selection, reverting to the app's default.

#### Scenario: Clearing a previously set color
- **WHEN** a user who previously set an accent color clears the selection
- **THEN** subsequent profile reads report no color identifier, meaning the app default applies again

### Requirement: Preferences are scoped to the authenticated user
The system SHALL ensure a user can only view or modify their own preferences, never another user's.

#### Scenario: Requests always act on the authenticated user
- **WHEN** an authenticated user views or updates preferences
- **THEN** the system only ever reads or writes that same user's own record, regardless of any other identifier
