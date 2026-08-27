## Why

"Balance del mes" reflects the full month's plan (paid and unpaid), not money that has actually moved. Users want to know how much they actually have available right now, without checking their bank, and want a simple savings figure so the app can flag when they're effectively dipping into savings.

## What Changes

- Add two simple, manually-set user fields: `ahorros` (a savings balance the user edits directly, no transaction history) and a "Disponible" baseline (`saldo_disponible_inicial` + the date it was set), following the same pattern as the existing `color_acento` preference.
- Setting/editing `saldo_disponible_inicial` always re-baselines the tracking date to today server-side — this avoids double-counting money already folded into the new manually-entered number.
- Add a new computed "Disponible" figure: `saldo_disponible_inicial` plus every paid `ingreso` entry and abono `interes` dated on/after the baseline date, minus every paid `deuda`/`gasto_fijo` entry and every `Gasto` dated on/after that date — an accumulating running total, not scoped to a single month.
- `ahorros` is never automatically adjusted by this computation — it stays a figure the user manages themselves; the API just exposes both numbers so the frontend can show a "you're effectively drawing on savings" warning when Disponible goes negative.

## Capabilities

### Modified Capabilities
- `user-preferences`: gains `ahorros` and the Disponible baseline as account-level preferences, alongside `color_acento`.

### New Capabilities
- `available-balance`: computes the running Disponible figure from paid entries, abono interest, and variable expenses since the baseline date.

## Impact

- `app/models/user.py`: `ahorros: Decimal | None`, `saldo_disponible_inicial: Decimal | None`, `saldo_disponible_fecha: date | None`.
- `app/schemas/user.py`: `UserRead`/`UserUpdate` gain the three fields; setting `saldo_disponible_inicial` in a PATCH always sets `saldo_disponible_fecha` server-side to today, ignoring any client-supplied date.
- New `app/routers` endpoint (e.g. `GET /summary/disponible`) and matching service function computing the running total described above, returning `None` when `saldo_disponible_fecha` is unset (feature not yet configured).
- New alembic migration adding the three nullable columns to `users`.
