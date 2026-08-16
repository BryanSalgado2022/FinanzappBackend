## 1. Data Model

- [x] 1.1 Add `tasa_interes` (nullable numeric), `periodo_tasa` (nullable enum `mensual`/`anual`), `numero_cuotas` (nullable int) to the `Concepto` model
- [x] 1.2 Write and run an Alembic migration adding these columns
- [x] 1.3 Update `ConceptoCreate` schema to accept the new fields, with validation: both `tasa_interes` and `numero_cuotas` required together (reject one without the other), and reject all three on `gasto_fijo`/`ingreso`

## 2. Amortization Calculation (spec: `budget-concepts`)

- [x] 2.1 Implement the monthly-rate conversion for `periodo_tasa = anual` (effective-rate formula, not flat `/12`)
- [x] 2.2 Implement the fixed-installment (French method) calculation given principal/monthly rate/installment count
- [x] 2.3 Implement full schedule generation (interest portion, principal portion, ending balance per installment), rounding so the final installment's balance is exactly zero
- [x] 2.4 Write tests: monthly vs. annual rate produces the correct converted rate, fixed installment matches a hand-computed example, schedule's final balance is zero, schedule totals reconcile (sum of principal portions = valor_total)

## 3. Immutability (spec: `budget-concepts`)

- [x] 3.1 Drop `valor_total`, `tasa_interes`, `periodo_tasa`, `numero_cuotas` from the fields `PATCH /concepts/{id}` accepts when the target concept has amortization data set
- [x] 3.2 Write tests: updating `valor_total` on an amortized debt is rejected; updating `valor_total` on a non-amortized debt still works as before

## 4. Auto-Generation Integration (spec: `monthly-budget`)

- [x] 4.1 On creating a debt concept with amortization data, generate monthly entries for the full schedule (all `numero_cuotas` installments, spanning multiple years if needed), each using that installment's fixed amount as `monto_planeado`
- [x] 4.2 Confirm non-amortized `deuda`/`gasto_fijo` auto-generation is unchanged (regression check against existing `add-budget-mvp` tests)
- [x] 4.3 Write tests: multi-year schedule generates entries beyond December of the creation year; generated amounts equal the schedule's fixed installment; non-amortized concepts are unaffected

## 5. Debts Summary (spec: `debts-summary`)

- [x] 5.1 Implement `GET /debts/summary`: total owed, total paid, overall remaining balance, overall percent progress, per-debt composition (name + remaining balance), scoped to the authenticated user
- [x] 5.2 Handle the no-debts case by returning zero totals, not an error
- [x] 5.3 Implement `GET /summary/annual?anio=`: total planned income and total planned expenses for each of the 12 months of the given year, scoped to the authenticated user
- [x] 5.4 Handle months with no entries by reporting zero, not omitting them
- [x] 5.5 Write tests covering: aggregation across multiple debts, zero-debts case, user scoping (user A never sees user B's debts in the summary), annual trend across months with and without entries

## 6. Wrap-up

- [x] 6.1 Run the full test suite and fix any failures
- [x] 6.2 Verify end-to-end locally via Docker Compose: create an amortized debt, confirm the generated schedule's amounts and that `PATCH` rejects editing its `valor_total`, and hit both new summary endpoints
- [x] 6.3 Update the backend README with the two new endpoints and the amortization field documentation
