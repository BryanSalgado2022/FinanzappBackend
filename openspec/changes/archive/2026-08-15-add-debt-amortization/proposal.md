## Why

Debts currently only track `valor_total` and a simple `saldo_restante` (total minus payments). The user's real debts (mortgage, bank loans) accrue interest under a standard fixed-installment schedule, and manually guessing next month's payment amount — as the user put it, "puse que la cuota es 100.000 pero por intereses termino pagando 130.000" — defeats the purpose of replacing the spreadsheet. This change adds real amortization math for debts that want it, plus the aggregate debt view and annual planned-vs-actual trend the user asked for after using the MVP.

## What Changes

- Add optional amortization fields to `deuda` concepts: `tasa_interes`, `periodo_tasa` (`mensual` | `anual`), `numero_cuotas`. When both `tasa_interes` and `numero_cuotas` are provided at creation, the system computes the fixed monthly installment (French/cuota-fija method) and generates the concept's amortization schedule (interest vs. principal per installment).
- When a debt has amortization data, its monthly entry auto-generation (existing behavior from `add-budget-mvp`) uses the schedule's fixed installment amount instead of copying the last-used amount forward.
- `valor_total`, `tasa_interes`, `periodo_tasa`, and `numero_cuotas` become immutable after creation on any concept that has amortization data — changing loan terms means deleting the concept and creating a new one, not editing in place. This is a **BREAKING** change to `PATCH /concepts/{id}`'s accepted fields for such concepts (previously `valor_total` was editable for all debts).
- Add a debts summary endpoint: total owed, total paid, overall percent progress, and per-debt composition, across all of a user's debts.
- Add an annual trend endpoint: total planned income/expenses per month for a given year (12 data points), to support a planned-vs-actual chart.

**BREAKING**: `valor_total` is no longer editable via `PATCH /concepts/{id}` for debt concepts that have amortization data (`tasa_interes`/`numero_cuotas` set). It remains editable for debts without amortization data, unchanged from today.

## Capabilities

### New Capabilities
- `debts-summary`: aggregate view across all of a user's debts (totals, overall progress, composition) and the annual planned-vs-actual trend.

### Modified Capabilities
- `budget-concepts`: debt concepts gain optional amortization fields (`tasa_interes`, `periodo_tasa`, `numero_cuotas`), a computed fixed installment and amortization schedule, and immutability of financial terms once set.
- `monthly-budget`: auto-generation for debts with amortization data uses the schedule's installment amount instead of the flat copy-forward behavior.

## Impact

- `FinanzappBackend`: new fields/table for amortization schedule, new endpoints (`GET /debts/summary`, `GET /summary/annual`), changed validation on concept creation/update.
- `FinanzappFrontend`: out of scope for this change — a separate change will add the "Deudas" screen and the annual trend chart once this API exists.
- No impact on debts without amortization data — fully backward compatible with concepts created under `add-budget-mvp`.

## Out of Scope (backlog, not part of this change)

- Editing/recalculating an existing amortization schedule (explicitly rejected by the user — delete and recreate instead).
- Envelope-style budget categories (Necesidades/Deseos/Deudas/Futuro).
- Any data import/migration tooling — the user will re-enter data manually going forward, not migrate historical spreadsheet data.
- Per-concept (non-aggregate) trend charts.
