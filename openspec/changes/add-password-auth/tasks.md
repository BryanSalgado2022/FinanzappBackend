## 1. Dependencies

- [x] 1.1 Add `bcrypt` to `requirements.txt`

## 2. Data model and migration

- [x] 2.1 In `app/models/user.py`, make `google_sub: str | None = Field(default=None, unique=True, index=True)` and add `password_hash: str | None = Field(default=None)`
- [x] 2.2 Generate and write an Alembic migration: `google_sub` becomes nullable, add nullable `password_hash` column
- [x] 2.3 Apply the migration against the docker compose `db` service

## 3. Password hashing

- [x] 3.1 Add `hash_password(password: str) -> str` and `verify_password(password: str, password_hash: str) -> bool` to `app/services/auth_service.py` using `bcrypt` directly (per design.md)

## 4. Service layer: register, login, linking

- [x] 4.1 Add `EmailAlreadyRegisteredError` and `InvalidCredentialsError` exception classes to `app/services/auth_service.py`
- [x] 4.2 Add `register_user(session, nombre, email, password) -> User`: reject if email exists (any account type), else create with `password_hash` set and no `google_sub`
- [x] 4.3 Add `authenticate_with_password(session, email, password) -> User`: raise `InvalidCredentialsError` for unknown email, no `password_hash` set, or wrong password - all three cases identical from the caller's perspective
- [x] 4.4 Update `get_or_create_user` to fall back to an email lookup and link `google_sub` onto an existing password-only account, per design.md's three-step lookup

## 5. Rate limiting

- [x] 5.1 Add an in-memory fixed-window rate limiter module (e.g. `app/services/rate_limit.py`) with a `check_rate_limit(request, key, limit, window_seconds)` function raising HTTP 429, plus a `reset_rate_limits()` function for test isolation, per design.md
- [x] 5.2 Apply the rate limiter to `/auth/register` and `/auth/login` (not `/auth/google`)

## 6. Schemas and router

- [x] 6.1 Add `RegisterRequest` (nombre, email, password with `min_length=8`) and `LoginRequest` (email, password) to `app/schemas/auth.py`
- [x] 6.2 Add `POST /auth/register` to `app/routers/auth.py`: calls `register_user`, maps `EmailAlreadyRegisteredError` to 409, returns `TokenResponse` via `create_access_token` on success
- [x] 6.3 Add `POST /auth/login` to `app/routers/auth.py`: calls `authenticate_with_password`, maps `InvalidCredentialsError` to 401 with a generic message, returns `TokenResponse` on success

## 7. Tests

- [x] 7.1 Add a `conftest.py` autouse fixture calling `reset_rate_limits()` before each test
- [x] 7.2 Test successful registration issues a token
- [x] 7.3 Test registration rejects a password shorter than 8 characters
- [x] 7.4 Test registration rejects an email already used by a Google account
- [x] 7.5 Test registration rejects an email already used by another password account
- [x] 7.6 Test successful login with correct email/password issues a token
- [x] 7.7 Test login with a wrong password and login with an unknown email both return the same error status/message
- [x] 7.8 Test login rejects a Google-only account (no password set) with the same generic error
- [x] 7.9 Test Google sign-in links to an existing password-only account by email (same account, no duplicate, existing data preserved) and returns a token that authenticates as that account
- [x] 7.10 Test exceeding the rate limit on `/auth/register` and on `/auth/login` returns 429
- [x] 7.11 Run the full test suite inside the `api` container and confirm all tests pass

## 8. Manual verification

- [x] 8.1 Restart the `api` container so the code changes take effect
- [x] 8.2 Verify via curl: register a new account, log in with it, confirm both return a working token (usable against a protected endpoint like `GET /concepts`)
- [x] 8.3 Verify via curl: registering with an email that already exists returns 409
- [x] 8.4 Verify via curl: logging in with a wrong password and with an unknown email both return the same 401 message
