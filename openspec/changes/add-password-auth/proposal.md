## Why

Google is currently the only way to sign in. Google OAuth configuration has already caused real login trouble for the user once, and the user asked for a typical email+password alternative so the app isn't fully dependent on Google being reachable/configured correctly.

## What Changes

- Add self-signup: `POST /auth/register` creates an account with name, email, and password. Rejects (409) if the email already exists under any login method.
- Add `POST /auth/login` with email+password, issuing the same JWT format already returned by `/auth/google`.
- Passwords are hashed with bcrypt, never stored or logged in plain text. Minimum 8 characters, no other complexity rules.
- `User.google_sub` becomes nullable; `User.password_hash` (nullable) is added. `User.email` stays unique across both login methods.
- Google sign-in gains account linking: if a Google sign-in's email matches an existing password-only account, the system links that account's `google_sub` instead of failing or duplicating - safe because the Google ID token cryptographically proves the requester owns that email. Registration never does the reverse (it always rejects an existing email, regardless of how that account was created), since password registration proves nothing about email ownership.
- Basic in-memory rate limiting on `/auth/register` and `/auth/login` (not `/auth/google`, which already requires a valid Google-issued token) to blunt brute-force/spam signups given there is no email verification.

Explicitly out of scope, left as future backlog: email verification, password-reset/"forgot password", and any frontend UI (a separate change).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `auth`: gains self-signup and password login as an alternative to Google OAuth, with account-linking and abuse-mitigation rules.

## Impact

- `app/models/user.py`: `google_sub` becomes nullable, new nullable `password_hash`.
- `alembic/versions/`: new migration.
- `app/schemas/auth.py`: new request/response schemas for register/login.
- `app/services/auth_service.py`: password hashing/verification, `get_or_create_user` gains email-based linking, new `register_user`/`authenticate_with_password` functions.
- `app/routers/auth.py`: new `/auth/register`, `/auth/login` endpoints; rate-limiting applied to both.
- `requirements.txt`: adds `bcrypt`.
- `tests/`: new coverage; `tests/conftest.py`'s `auth_headers` pattern is unaffected (still simulates Google sign-in).
