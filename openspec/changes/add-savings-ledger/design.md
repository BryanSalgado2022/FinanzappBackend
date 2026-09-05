## Context

See proposal.md for motivation. This mirrors the existing `Abono` pattern (`app/models/deudor.py`) for the ledger shape, and `concept_service.saldo_restante`/`deudor_service.saldo_restante`'s "always computed, never stored" pattern for the running balance.

## Goals / Non-Goals

**Goals:**
- Replace the single overwritable `ahorros` figure with an auditable, dated ledger.
- Keep the running balance cheap to read (computed inline, no extra round-trip) since it's shown on the Dashboard.

**Non-Goals:**
- No linkage between this ledger and `summary_service.py`'s monthly summary or `balance_neto` — withdrawals are informational only (see the durable spec requirement for this; it is not an oversight to revisit).
- No frontend work (sibling change `add-savings-ledger-ui`).

## Decisions

### New `AporteAhorro` model, not a reused/generic entity
`Abono` is scoped to a `Deudor` (`deudor_id`); savings belong directly to a `User`, with no intermediate owning entity. A new model (`AporteAhorro`, table `aportes_ahorro`, FK `user_id → users.id`) keeps this simple rather than forcing an artificial parent entity. `monto` is always stored positive; direction comes from `tipo` (`aporte`/`retiro`), not sign — this keeps the stored amount always human-readable (matches what the user typed) and keeps the "is this an expense or income direction" concern in one enum field rather than encoded implicitly in a sign convention that every reader of the table would need to remember.

### `ahorros` becomes computed, not stored
Mirrors `saldo_restante`: computed as `sum(monto where tipo=aporte) - sum(monto where tipo=retiro)`, defaulting to zero. Keeping the same field name (`UserRead.ahorros`) minimizes churn for callers that already read it (the Dashboard's `SavingsCard`), even though its write path is now gone. Computed inline in `get_me`/`update_me` (both already return `UserRead`) rather than via a separate "balance" endpoint, since the Dashboard already fetches `/users/me` for other preferences and a separate round-trip just for this number would be wasteful.

### Withdrawals carry zero automatic linkage — a hard constraint, not an oversight
The `remove-disponible` change deliberately removed automatic "planned - spent = disponible" tracking because it confused the user about where numbers came from. Reviving any automatic link between a `retiro` and the monthly summary or `balance_neto` would reintroduce exactly that confusion under a different name. This is encoded as its own durable spec requirement precisely so a future change can't "fix" it as an apparent inconsistency without deliberately revisiting this decision.

### Endpoints are top-level, not nested
`Abono` endpoints nest under `/deudores/{deudor_id}/abonos` because a `Deudor` owns them. Savings entries have no such owning entity other than the user themselves (already the implicit scope of every authenticated endpoint), so `/ahorros`, not `/users/me/ahorros` or similar — shorter, and consistent with how the API doesn't nest other purely-user-scoped resources under `/users/me`.

## Risks / Trade-offs

- **Migration is a real schema change (column drop) on a live table.** Mitigated by running the data-copy step before the drop, in the same migration, so no window exists where a value could be lost between copy and drop.
- **Downgrade is lossy** (see Migration Plan) — accepted, consistent with `remove-disponible`'s precedent of not preserving perfect reversibility for a deliberate one-way feature change.

## Migration Plan

Single Alembic revision:
1. Create the `tipoaporte` enum type and `aportes_ahorro` table.
2. Data migration: for every user with a non-null `ahorros` value, insert one `AporteAhorro` row (`tipo='aporte'`, `monto=`that value, `fecha=`the migration's run date).
3. Drop the `ahorros` column from `users`.

Downgrade (best-effort, lossy): recreate the nullable `ahorros` column, backfill each user's value from their then-current computed ledger balance (sum of aporte minus retiro), then drop `aportes_ahorro`. Individual entries, their dates, and any history are not recoverable on downgrade — this is an accepted trade-off for a deliberate one-way migration, not a bug to fix.
