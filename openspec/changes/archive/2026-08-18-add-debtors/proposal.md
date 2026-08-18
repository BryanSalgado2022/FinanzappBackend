## Why

The user wants to track money other people owe *them* — the mirror image of a `deuda` concept (money the user owes). This is the third and final of three future-facing ideas noted on 2026-08-18; the other two (Tareas/citas and Categorías) are already shipped. Right now there is no way to record "I lent Juan $500,000 on this date" or track partial repayments toward it.

## What Changes

- Add a new `Deudor` entity per user: `nombre` (required), `monto_total` (required), `fecha` (required — since when the loan was made), `garantia` (optional free text; empty means no collateral was left), `activo` (boolean, defaults to true — lets a debtor record be closed independent of whether it's fully repaid).
- Add a new `Abono` entity (partial payment) per `Deudor`: `monto`, `fecha` — nothing else.
- `Deudor` responses include a computed `saldo_restante` (`monto_total` minus the sum of its abonos), mirroring how a debt concept's remaining balance is computed today — never stored.
- Full CRUD for `Deudor` (create, list, get, update, delete) and for its `Abono`s (create, list, delete — no update, since a wrong abono is deleted and re-created rather than edited).
- No summary/aggregate endpoint — the three summary figures a future UI needs (total owed, number of debtors, number with collateral) are cheap to compute client-side from the list response, which already carries `saldo_restante` per debtor.
- No integration with any existing screen or endpoint (Dashboard, concepts, summary) — debtors are entirely standalone, same as categories and tasks.

## Capabilities

### New Capabilities
- `debtor-management`: CRUD for the `Deudor` entity and its `Abono` payments, including the computed remaining-balance figure.

## Impact

- Backend only: new `app/models/deudor.py` (both `Deudor` and `Abono`), `app/schemas/deudor.py`, `app/services/deudor_service.py`, `app/routers/deudores.py`, and a new Alembic migration (pure schema addition, no data migration needed).
- No frontend changes in this change — a separate frontend change will consume the new endpoints once this is applied.
- No changes to any existing capability or endpoint.
