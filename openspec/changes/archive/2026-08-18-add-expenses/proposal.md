## Why

The app can plan and track monthly-recurring money movements (`deuda`, `gasto_fijo`, `ingreso`) but has no way to record an ad-hoc, variable-amount expense that happens on a specific day — e.g. spending $20,000 on a pizza. Today that spending is simply invisible to the app, so the monthly balance overstates how much money the user actually has left.

## What Changes

- Add a new standalone `Gasto` entity: `monto`, `fecha`, `descripcion` (all required), with an optional many-to-many assignment to existing `Categoria` entities via a new `GastoCategoria` link table.
- Full CRUD for `Gasto` (create, list filtered by year/month, get, update, delete), unrestricted by date — no fixed-schedule rules like amortized debts have.
- `monthly_summary` now also subtracts the sum of a user's `Gasto.monto` falling in the requested year/month (by `fecha`) from `total_gastos`, alongside the existing planned `deuda`/`gasto_fijo` totals.
- No category-level aggregation/reporting endpoints in this change (e.g. "total spent per category") — categorization is captured and displayed, but rollups stay future backlog.

## Capabilities

### New Capabilities
- `expense-management`: create, read, update, delete ad-hoc variable expenses, each with an amount, a date, a description, and optional categories.

### Modified Capabilities
- `monthly-budget`: the "Monthly net balance summary" requirement changes so `total_gastos` (and therefore `balance_neto`) also accounts for the user's variable expenses recorded for that year/month, not just planned `deuda`/`gasto_fijo` amounts.

## Impact

- New: `app/models/gasto.py`, `app/schemas/gasto.py`, `app/services/gasto_service.py`, `app/routers/gastos.py`, a `GastoCategoria` link table, an Alembic migration, tests.
- Modified: `app/services/summary_service.py` (`monthly_summary` now also sums `Gasto`), `app/main.py` (router registration), `app/models/__init__.py`, `README.md`.
- No changes to `Concepto`/`EntradaMensual` or their existing endpoints.
