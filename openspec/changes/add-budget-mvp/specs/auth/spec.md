## Purpose

Lets users sign in with their Google account and ensures every subsequent request is scoped to their own data, with no password of their own to manage.

## ADDED Requirements

### Requirement: Google OAuth sign-in
The system SHALL allow a user to authenticate using Google OAuth instead of a system-managed password.

#### Scenario: User signs in with Google
- **WHEN** a user completes the Google OAuth flow with a valid Google account
- **THEN** the system issues the user an authenticated session/token they can use for subsequent API requests

#### Scenario: OAuth flow fails or is denied
- **WHEN** the Google OAuth flow fails, expires, or the user denies consent
- **THEN** the system rejects the sign-in attempt and does not issue a session/token

### Requirement: Automatic user provisioning
The system SHALL create a user record automatically the first time a given Google account signs in, without requiring a separate registration step.

#### Scenario: First-time Google sign-in
- **WHEN** a Google account authenticates for the first time and no matching user record exists
- **THEN** the system creates a new user record linked to that Google account and signs the user in

#### Scenario: Returning user sign-in
- **WHEN** a Google account authenticates and a matching user record already exists
- **THEN** the system signs the user into their existing account without creating a duplicate

### Requirement: Requests are scoped to the authenticated user
The system SHALL require a valid authenticated session for all budget data endpoints and SHALL scope every read or write to the requesting user's own data.

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request to a budget data endpoint has no valid session/token
- **THEN** the system rejects the request with an authentication error and performs no data access

#### Scenario: User cannot access another user's data
- **WHEN** an authenticated user requests or modifies a concept or monthly entry owned by a different user
- **THEN** the system denies the request and does not return or modify that data
