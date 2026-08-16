## Context

See proposal.md for motivation. Relevant current state:

- `app/models/user.py`: `User.google_sub` is `str` (NOT NULL, unique); `User.email` is unique. No password field exists.
- `app/services/auth_service.py`: `get_or_create_user(session, google_sub, email, name)` looks up strictly by `google_sub`, creating a new row if none matches - it never consults `email`. `create_access_token`/`decode_access_token` are generic (just encode/decode `user.id`) and need no changes.
- `app/routers/auth.py`: `/auth/google` and `/auth/dev-login` follow a simple pattern - verify/derive identity, call a service function, wrap in `TokenResponse`.
- `tests/conftest.py`'s `auth_headers` monkeypatches `verify_google_id_token` and hits `/auth/google` - unaffected by this change, but the in-memory SQLite test DB (fresh per test via the `engine` fixture) and the single shared `app` object matter for the rate-limiter design below.
- No password-hashing or rate-limiting dependency exists in `requirements.txt` today.

## Goals / Non-Goals

**Goals:**
- Email/password as a fully independent second way to reach the same account model and JWT.
- Minimal new infrastructure - no Redis, no external rate-limiting service, no email provider.

**Non-Goals:**
- Email verification, password reset - explicitly deferred (see proposal.md).
- Multi-instance/multi-worker-safe rate limiting - the app runs as a single uvicorn process in docker compose today; a future move to multiple workers/instances would need a shared store (Redis) instead of the in-memory approach chosen here.

## Decisions

### Hash with the `bcrypt` package directly, not `passlib`
`passlib` is in maintenance mode and has a well-known compatibility break with recent `bcrypt` releases (`passlib` reads a `__about__.__version__` attribute that newer `bcrypt` versions removed, causing a warning/failure at import time unless versions are pinned carefully). Using `bcrypt` directly avoids that fragile pairing for a two-function need (`bcrypt.hashpw`/`bcrypt.checkpw`). Add `bcrypt` to `requirements.txt`.

```python
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())
```

### `User` model changes and the linking lookup
```python
google_sub: str | None = Field(default=None, unique=True, index=True)
password_hash: str | None = Field(default=None)
```
`get_or_create_user` (used by `/auth/google`) changes from "find by `google_sub` or create" to:
1. Look up by `google_sub` - if found, return it (existing behavior, unchanged).
2. Else, look up by `email` - if found (a password-only account with no `google_sub`), set its `google_sub` and return it (the new linking behavior).
3. Else, create a new user with `google_sub` set and no `password_hash` (existing behavior, unchanged).

`/auth/register` calls a new `register_user(session, nombre, email, password)`:
1. Look up by `email` - if found (regardless of whether it has `google_sub` or `password_hash`), raise a `EmailAlreadyRegisteredError` → router returns 409.
2. Else, create a new user with `password_hash` set and no `google_sub`.

`/auth/login` calls a new `authenticate_with_password(session, email, password) -> User`:
1. Look up by `email`. If not found, or found but `password_hash` is `None` (a Google-only account), or `verify_password` fails → raise a single `InvalidCredentialsError` in every case, so the router's error response is identical regardless of which sub-case occurred (matches the "same generic error" requirement).

### Rate limiting: a small in-memory fixed-window counter, no new dependency
A module-level `dict[str, list[float]]` (keyed by client IP + endpoint name) storing recent-request timestamps, pruned on each check. A `check_rate_limit(request: Request, key: str, limit: int, window_seconds: int)` dependency-style function raises `HTTPException(429)` when exceeded. Applied to `/auth/register` and `/auth/login` only (not `/auth/google`, which already requires a Google-signed token as its own gate). Limit: a generous-but-real value like 10 attempts per 5 minutes per IP per endpoint - loose enough not to bother a real user mistyping their password a few times, tight enough to blunt scripted abuse.

Alternative considered: `slowapi` (a real dependency, Redis-optional). Rejected - it's more machinery than a single-process personal app needs, and the hand-rolled version is ~15 lines with zero new dependencies.

**Test isolation risk**: the counter dict lives at module scope, shared across the whole test session via the single imported `app`/module. A test file that calls `/auth/login` or `/auth/register` more than the limit across multiple tests could trip the limiter unexpectedly. Mitigation: expose a `reset_rate_limits()` function in the rate-limit module and call it from a `conftest.py` autouse fixture before each test, keeping the limiter itself simple while keeping tests deterministic.

### Router error mapping
- `EmailAlreadyRegisteredError` → 409 Conflict (`/auth/register`).
- `InvalidCredentialsError` → 401 Unauthorized (`/auth/login`), body message: "Invalid email or password" (never mentions which part was wrong).
- Rate limit exceeded → 429 Too Many Requests.

## Risks / Trade-offs

- **[Risk]** In-memory rate limiting resets on process restart and doesn't share state across multiple workers/instances. → Acceptable now (single process, documented as a Non-Goal); revisit with Redis if the deployment topology changes.
- **[Risk]** No email verification means a registered email isn't proven to belong to the registrant. → Accepted per grilling; the asymmetric linking rule (Google can link, password registration can't) is the specific mitigation for the one dangerous case (account takeover via registration); rate limiting mitigates spam/brute-force. Full email verification stays explicit future backlog.
- **[Trade-off]** `google_sub` becoming nullable weakens a previously-total invariant ("every user has a Google identity"). → Necessary for password-only accounts to exist at all; every code path that currently assumes `google_sub` is non-null needs a check (see tasks.md) - this is a deliberate, scoped model change, not a side effect.
