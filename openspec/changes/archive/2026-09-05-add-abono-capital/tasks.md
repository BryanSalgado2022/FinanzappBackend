## 1. Math

- [x] 1.1 In `app/services/amortization_service.py`, add `calcular_cuotas_restantes(principal, tasa_mensual, cuota_fija) -> int`: simulate the same per-period interest/capital split as `generar_tabla_amortizacion`, incrementing a counter until the balance reaches zero. Raise `ValueError` if `cuota_fija` doesn't cover a period's interest (would never converge). Handle `tasa_mensual == 0` as a straight-line ceiling division.

## 2. Schema

- [x] 2.1 In `app/schemas/deudor.py`, add `ModoAbonoCapital` enum (`REDUCIR_PLAZO="reducir_plazo"`, `REDUCIR_CUOTA="reducir_cuota"`) and `AbonoCapitalCreate { monto: Decimal (gt=0), fecha: date, modo: ModoAbonoCapital }`.

## 3. Service logic

- [x] 3.1 In `app/services/deudor_service.py`, change `cuota_fija(session, deudor)` to read the next not-yet-paid `CuotaDeudor.monto_planeado` (falling back to the most recent cuota if none unpaid, or the stored-terms computation if no cuotas exist at all). Update its call site in `app/routers/deudores.py`'s `_to_read`.
- [x] 3.2 Change `saldo_restante`'s amortized branch to also subtract `sum(Abono.monto - coalesce(Abono.interes, 0))` for that debtor, alongside the existing paid-cuota sum.
- [x] 3.3 Add `registrar_abono_capital(session, user_id, deudor_id, *, monto, fecha, modo) -> Deudor`: fetch deudor (404), reject if not `es_amortizado` (`ValueError`), create the `Abono` (`interes=None`), recompute `saldo_restante`. If it's now `<= 0`: delete every not-yet-paid `CuotaDeudor`, mark the debtor finished if not already (mirrors the existing `activo`/`finalizado_en` transition), return. Otherwise: compute `siguiente_numero` and the anchor date exactly like `actualizar_amortizacion` does, compute `numero_cuotas_restantes` (unchanged remaining count for `reducir_cuota`, or via `calcular_cuotas_restantes` for `reducir_plazo` using the *current* `cuota_fija`), delete every not-yet-paid `CuotaDeudor`, update `deudor.numero_cuotas` to the new total, generate the remaining schedule via `generar_tabla_amortizacion` + `cuota_deudor_service.generar_cuotas_amortizacion(..., cuota_inicial=1)`.

## 4. Router

- [x] 4.1 Add `POST /deudores/{deudor_id}/abono-capital` in `app/routers/deudores.py` calling `registrar_abono_capital`, 404 on not found, 422 on `ValueError`, returning `DeudorRead`.

## 5. Tests

- [x] 5.1 Add tests: `reducir_plazo` keeps the fixed installment (aside from rounding) and shortens the schedule; `reducir_cuota` keeps the installment count and lowers the fixed installment; paid installments untouched; full prepayment marks the debtor finished and clears remaining installments; rejected on non-amortized debtor; `reducir_plazo` rejected when the installment no longer covers interest; `monto_total` unchanged by a prepayment (still shows the original loan amount); cross-user 404 scoping.
- [x] 5.2 Confirm existing `cuota_fija`/`saldo_restante` tests for creation, correction, and activation still pass unchanged (proving the schedule-derived `cuota_fija` and abono-aware `saldo_restante` are backward compatible).
- [x] 5.3 Run the full backend test suite and confirm everything passes.
