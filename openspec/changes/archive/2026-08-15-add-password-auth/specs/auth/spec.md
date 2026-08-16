## ADDED Requirements

### Requirement: Password-based self-signup
The system SHALL allow a user to create an account by providing a name, email, and password (minimum 8 characters), and SHALL reject the request if an account with that email already exists, regardless of whether that existing account was created via Google or via password.

#### Scenario: Successful registration
- **WHEN** a user registers with a name, a new email, and a password of at least 8 characters
- **THEN** the system creates the account, hashes and stores the password, and issues the same kind of authenticated session/token as Google sign-in

#### Scenario: Reject a password shorter than the minimum
- **WHEN** a user attempts to register with a password shorter than 8 characters
- **THEN** the system rejects the request and does not create an account

#### Scenario: Reject registration with an email already in use
- **WHEN** a user attempts to register with an email that already belongs to an existing account, whether that account was created via Google or via password
- **THEN** the system rejects the request without modifying the existing account

### Requirement: Password login
The system SHALL allow a user with a password-enabled account to authenticate with their email and password, issuing the same kind of authenticated session/token as Google sign-in on success.

#### Scenario: Successful password login
- **WHEN** a user submits the correct email and password for an account that has a password set
- **THEN** the system issues an authenticated session/token

#### Scenario: Wrong password or unknown email produce the same error
- **WHEN** a user submits a password that does not match, or an email with no matching account
- **THEN** the system rejects the request with the same generic invalid-credentials error in both cases, without indicating whether the email exists

### Requirement: Google sign-in links to an existing password account by email
The system SHALL, when a Google sign-in's verified email matches an existing account that has no Google identity linked, link that Google identity to the existing account rather than rejecting the sign-in or creating a duplicate account.

#### Scenario: Google sign-in links a password-only account
- **WHEN** a user signs in with Google using an email that already has a password-only account and no linked Google identity
- **THEN** the system links the Google identity to that existing account and signs the user in, preserving the account's existing password and data

#### Scenario: Password registration never links to an existing Google account
- **WHEN** a user attempts to register with a password using an email that already has a Google-linked account
- **THEN** the system rejects the registration exactly as it would for any other already-used email, without linking or modifying the existing account

### Requirement: Registration and password login are rate-limited
The system SHALL apply a rate limit to `/auth/register` and `/auth/login` to blunt automated abuse, given the absence of email verification.

#### Scenario: Excessive attempts are rejected
- **WHEN** a client exceeds the configured number of registration or login attempts within the configured time window
- **THEN** the system rejects further attempts from that client until the window resets, without attempting the underlying registration or login logic
