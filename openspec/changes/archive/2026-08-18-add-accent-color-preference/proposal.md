## Why

The user wants to personalize their account with an accent color that gives each budget visual identity. This needs to be tied to the account (not the device) so it follows the user across browsers/devices, which today's model has no place for.

## What Changes

- Add a nullable `color_acento` field to `User`, restricted to a curated set of allowed identifiers (validated server-side, same pattern as `ALLOWED_CATEGORIA_EMOJIS`). `None` means "use the app's default color."
- Add a new `users` router: `GET /users/me` (returns the current user's profile including `color_acento`) and `PATCH /users/me` (updates `color_acento`).
- No color/CSS logic lives in the backend - it only stores and returns the chosen identifier. Translating that identifier into actual colors (light/dark values, `accent-soft` derivation) is entirely a frontend concern, covered by a separate follow-up change.

## Capabilities

### New Capabilities
- `user-preferences`: lets a user view and update their own account-level preferences, starting with their accent color choice.

### Modified Capabilities
(none)

## Impact

- New: `app/schemas/user.py`, `app/routers/users.py`, an Alembic migration, tests.
- Modified: `app/models/user.py` (new field + allowed-values constant), `app/main.py` (router registration), `README.md`.
- No changes to existing auth endpoints or JWT contents.
