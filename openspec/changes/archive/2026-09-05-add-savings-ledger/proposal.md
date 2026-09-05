## Why

`User.ahorros` today is a single manually-editable number the user can only ever overwrite, with no history of how it grew or shrank. The user explicitly asked for a place to add savings funds at any time that increments over time, and later clarified withdrawals need tracking too — both call for a dated ledger, not a single overwritable figure.

## What Changes

- Replace the single `User.ahorros` value with a dated ledger of contributions and withdrawals (`aporte`/`retiro`), mirroring how `Abono` already tracks debtor repayments.
- The user's savings balance becomes a computed running total (sum of aportes minus sum of retiros) instead of a manually-set number.
- **BREAKING**: `PATCH /users/me` no longer accepts `ahorros` — it is set exclusively through the new ledger endpoints now.
- A user's existing non-null `ahorros` value is migrated into their ledger as a first `aporte` entry, dated the day this change deploys; the old column is then dropped.
- Withdrawals (`retiro`) are purely manual bookkeeping: recording one has zero automatic effect on the monthly summary, `balance_neto`, or any other calculation — this is a hard constraint, not an oversight to "fix" later.

## Capabilities

### New Capabilities
- `savings-tracking`: lets a user record dated savings contributions and withdrawals, view their history, delete an entry, and see a computed running balance — with withdrawals never automatically affecting any other balance calculation.

### Modified Capabilities
- `user-preferences`: `ahorros` is no longer a manually-set preference — it becomes a computed, always-present figure sourced from `savings-tracking`, and is no longer settable via `PATCH /users/me`.

## Impact

- `app/models/user.py`: `ahorros` column removed.
- New `app/models/aporte_ahorro.py`: `AporteAhorro` model, `TipoAporte` enum.
- New Alembic migration: create `aportes_ahorro` table, migrate existing non-null `ahorros` values into seed ledger entries, drop the `ahorros` column.
- New `app/services/ahorro_service.py`, `app/schemas/ahorro.py`, `app/routers/ahorros.py` (`POST /ahorros`, `GET /ahorros`, `DELETE /ahorros/{id}`).
- `app/schemas/user.py`: `UserRead.ahorros` becomes a computed non-nullable field; `UserUpdate.ahorros` removed.
- `app/routers/users.py`: `get_me`/`update_me` compute `ahorros` via `ahorro_service`; the `ahorros` PATCH branch is removed.
- `app/services/summary_service.py`: untouched by this change — confirmed no linkage added.
- Frontend impact (sibling change `add-savings-ledger-ui`, not this change's concern): `SavingsCard.tsx`'s inline edit and `useUpdateUserPreferences` become obsolete, replaced by ledger creation/history UI.
