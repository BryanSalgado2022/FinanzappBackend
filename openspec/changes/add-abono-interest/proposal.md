## Why

Some loans to debtors carry interest. Today an abono is purely principal — there's no way to record that part of a payment was interest, and interest income has no effect on the user's monthly income totals even when it should.

## What Changes

- Add an optional `interes` field to abono creation, representing how much of that payment's `monto` was interest rather than principal repayment. `interes`, when provided, MUST NOT exceed `monto`.
- The debtor's `saldo_restante` computation changes to subtract only the principal portion of each abono (`monto - interes`), not the full `monto` — interest doesn't reduce what's still owed on the original loan.
- The `interes` amount of every abono recorded in a given month contributes to that month's `total_ingresos` in the monthly summary, alongside planned `ingreso` concept entries.

## Capabilities

### Modified Capabilities
- `debtor-management`: abono creation gains the optional `interes` field, and remaining-balance computation changes to use principal only.
- `monthly-budget`: monthly net balance summary's `total_ingresos` gains abono interest as a contributing source.

## Impact

- `app/models/deudor.py`: `Abono.interes: Decimal | None`.
- `app/schemas/deudor.py`: `AbonoCreate`/`AbonoRead` gain `interes`, with a validator rejecting `interes > monto`.
- `app/services/deudor_service.py`: `saldo_restante` computation changes from `monto_total - sum(monto)` to `monto_total - sum(monto - coalesce(interes, 0))`.
- `app/services/summary_service.py`: `total_ingresos` additionally sums `Abono.interes` for abonos whose `fecha` falls in the requested `anio`/`mes`, across all of the user's debtors.
- New alembic migration adding the nullable `interes` column to the `abonos` table.
