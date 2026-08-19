## Why

The upcoming "Agenda de pagos" calendar view (frontend, separate change) needs three pieces of data the backend doesn't expose today: a day-of-month for `ingreso` concepts, the exact day a monthly entry was paid, and the exact day a debt (concept or debtor) was closed out — so it can place events on specific calendar days and celebrate payoffs.

## What Changes

- `Concepto.dia_vencimiento` becomes available to `ingreso` concepts too (today rejected for that type) - same field, same semantics (optional, 1-28, always editable), just no longer restricted by type.
- `EntradaMensual` gains `fecha_pago` (nullable date): set automatically to today's date the moment an entry becomes `pagado=true` (if not already paid), cleared if it's marked unpaid again. Lets the frontend place "this installment was paid" on an exact calendar day instead of only knowing the year/month.
- `Concepto` gains `finalizado_en` (nullable date): set automatically to today's date the moment `activo` flips from `true` to `false`, cleared if reactivated. Lets the frontend mark the exact day a debt/concept was closed.
- `Deudor` gains `finalizado_en` (nullable date), same semantics as above, for closing a debtor.

## Capabilities

### Modified Capabilities
- `budget-concepts`: the due-day requirement now allows `ingreso`; the update/finish requirement now records when a concept was finished.
- `monthly-budget`: the monthly-entry requirement now records the exact date an entry was paid.
- `debtor-management`: the update/close requirement now records when a debtor was closed.

## Impact

- Modified: `app/models/concepto.py`, `app/models/entrada_mensual.py`, `app/models/deudor.py`, `app/schemas/concepto.py`, `app/schemas/entrada_mensual.py`, `app/schemas/deudor.py`, `app/services/concept_service.py`, `app/services/entry_service.py`, `app/services/deudor_service.py`, three Alembic migrations (or one combined), `README.md`, existing tests that assert the old `ingreso` rejection.
- No new endpoints or routers - all three additions extend existing create/update flows.
