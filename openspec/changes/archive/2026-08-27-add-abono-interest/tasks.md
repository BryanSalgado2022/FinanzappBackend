## 1. Model and migration

- [x] 1.1 Add `interes: Decimal | None` to `Abono` in `app/models/deudor.py`.
- [x] 1.2 Generate and review the alembic migration adding the nullable `interes` column to `abonos`.

## 2. Schema and validation

- [x] 2.1 Add `interes: Decimal | None = None` to `AbonoCreate` and `interes: Decimal | None` to `AbonoRead` in `app/schemas/deudor.py`.
- [x] 2.2 Add a validator rejecting `interes > monto` on `AbonoCreate`.

## 3. Service logic

- [x] 3.1 Update `saldo_restante` computation in `app/services/deudor_service.py` to subtract `sum(monto - coalesce(interes, 0))` instead of `sum(monto)`.
- [x] 3.2 Update `app/services/summary_service.py`'s `total_ingresos` computation to additionally sum `Abono.interes` (joined through `Deudor` to scope by `user_id`) for abonos whose `fecha` falls in the requested `anio`/`mes`.

## 4. Tests

- [x] 4.1 Add/update tests in `tests/test_deudores.py` (or equivalent): recording an abono with `interes` succeeds; `interes > monto` is rejected; `saldo_restante` reflects principal-only reduction.
- [x] 4.2 Add/update tests in `tests/test_summary.py` (or equivalent): an abono's `interes` in the requested month contributes to `total_ingresos`/`balance_neto`; an abono with no `interes` does not affect the summary; an abono in a different month does not contribute.
- [x] 4.3 Run the full test suite and confirm it passes.
