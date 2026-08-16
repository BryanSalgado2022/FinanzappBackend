## Why

The user currently manages debts, fixed expenses, income, and monthly cash flow manually in a spreadsheet ("Presupuesto1"), rebuilding formulas and copying rows every month. This change delivers the backend API for a budgeting app that replaces that spreadsheet: users can register recurring financial concepts (debts, fixed expenses, income), track them month by month, and get an automatic monthly balance calculation.

## What Changes

- Add Google OAuth login; a user record is created automatically on first sign-in (no password-based auth).
- Add CRUD for **Concepts** (`Concepto`): user-owned financial line items with a free-form name, a type (`deuda` | `gasto_fijo` | `ingreso`), an optional free-form category, and an active/finished status. Concepts persist indefinitely across years until finished or deleted.
- Add debt-specific behavior for concepts of type `deuda`: a `valor_total` field and a computed remaining balance (`valor_total` minus the sum of all historical `monto_pagado` across every year). The data model leaves room for future amortization fields (interest rate, installment count) without requiring them now.
- Add CRUD for **Monthly Entries** (`EntradaMensual`): one entry per concept per year/month, with `monto_planeado`, `monto_pagado` (nullable), and a `pagado` status. Creating or editing a recurring concept auto-generates entries for the remaining months of the current year using the last amount used.
- Add a monthly summary endpoint that computes `balance_neto` for a given user/year/month as the sum of planned income minus the sum of planned debt and fixed-expense amounts.
- Single currency (COP) only; no multi-currency support.

**BREAKING**: None (new system, no prior API).

## Capabilities

### New Capabilities
- `auth`: Google OAuth login and automatic user provisioning on first sign-in.
- `budget-concepts`: CRUD for user-owned financial concepts (debts, fixed expenses, income), including debt total/remaining-balance tracking.
- `monthly-budget`: Per-concept monthly planned/paid entries (with auto-generation for recurring concepts) and the monthly net balance summary.

### Modified Capabilities
(none — greenfield project)

## Impact

- New FastAPI backend service (`FinanzappBackend`) backed by PostgreSQL, using SQLModel/SQLAlchemy + Alembic migrations.
- New database schema: users, concepts, monthly entries.
- No impact on other systems yet — the React frontend (`FinanzappFrontend`) consumes this API in a separate, later change.

## Out of Scope (backlog, not part of this change)

- Natural-language expense entry with AI-based auto-categorization.
- Real debt amortization calculations (interest rate, installment schedules).
- Annual budgets as an independent entity (annual totals are a computed view over 12 monthly entries).
- Multi-currency support.
- Advanced/automatic recurrence beyond the simple same-year auto-generation described above.
- Reporting/charts, and Excel/PDF export.
- Notion or other external task-tracking integration.
