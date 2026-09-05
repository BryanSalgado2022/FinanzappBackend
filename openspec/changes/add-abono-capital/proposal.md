## Why

An amortized debtor's schedule assumes payments always match the fixed installment exactly. In reality a debtor can pay extra toward principal at any time ("abono a capital" / prepayment) — today there's no way to record that on an amortized debtor at all (regular abono creation is explicitly blocked once amortized), and the schedule has no mechanism to reflect it.

## What Changes

- New `POST /deudores/{deudor_id}/abono-capital` records an extraordinary principal payment (`monto`, `fecha`) against an amortized debtor, reusing the existing `Abono` record (with `interes` always null, since it's pure principal by definition) for history.
- The caller chooses, per payment, how the reduced principal is applied to the remaining schedule: **reducir_plazo** (same fixed installment, fewer remaining installments) or **reducir_cuota** (same remaining installment count, a lower fixed installment).
- If the payment fully settles the remaining balance, the debtor is automatically marked finished (mirrors the existing `activo`/`finalizado_en` transition).
- Rejected (422) on a non-amortized debtor (use the regular abono endpoint instead), and on `reducir_plazo` when the fixed installment wouldn't even cover the reduced balance's interest.

## Capabilities

### Modified Capabilities
- `debtor-management`: adds principal prepayments on amortized debtors, alongside the existing regular-abono (non-amortized only) and schedule-correction behavior.

## Impact

- `app/services/amortization_service.py`: new pure function `calcular_cuotas_restantes` (the inverse of `calcular_cuota_fija` — given a fixed installment and remaining principal, how many installments are needed).
- `app/services/deudor_service.py`: new `registrar_abono_capital`; `saldo_restante`'s amortized branch also subtracts principal-only abonos; `cuota_fija` becomes schedule-derived (reads the next unpaid `CuotaDeudor`'s planned amount) instead of recomputed from stored terms, so it stays correct after a prepayment changes the remaining schedule without altering the debtor's original `monto_total`/`numero_cuotas` (kept as historical record of the original loan).
- `app/schemas/deudor.py`: new `ModoAbonoCapital` enum, `AbonoCapitalCreate` schema.
- `app/routers/deudores.py`: new endpoint; `_to_read` passes `session` through to the now schedule-derived `cuota_fija`.
- Out of scope (confirmed with the user): `Concepto` (the user's own debts) has no equivalent payment-ledger entity to extend cleanly for this — not addressed in this change.
