## Why

A user can't record a debtor (`Deudor`) who owes them money at an interest rate — today a `Deudor` only supports `monto_total` plus free-form `Abono` repayments, with no way to capture the terms of a loan made at a known rate (e.g. lending a friend money at X% and expecting a fixed monthly payment back). The user explicitly asked for this, and confirmed it should work exactly like the app's existing `deuda`-type `Concepto` amortization: a computed fixed installment and an automatically generated schedule, editable later using the same recalculation logic already shipped for concepts (`add-edit-amortized-debt`).

## What Changes

- `Deudor` gains optional amortization terms (`tasa_interes`, `periodo_tasa`, `numero_cuotas`, `cuota_inicial`) — a field-for-field mirror of `Concepto`'s amortization fields, with the same validation and immutability rules. A `Deudor` with no `tasa_interes` set is entirely unaffected: free-form `Abono` creation keeps working exactly as it does today.
- When amortization terms are set at creation, the system generates a fixed monthly installment schedule anchored to the debtor's own `fecha`, computed with the same french/constant-payment method already used for concepts (`amortization_service.py`, reused unchanged).
- New capability: a `CuotaDeudor` entity parallel to `EntradaMensual` but keyed by `deudor_id` — one row per scheduled installment, supporting recording the actual amount paid (mirrors `monto_planeado`/`monto_pagado`/`pagado`/`fecha_pago`). Each installment also carries its planned `interes` component, since only the interest portion of a received payment is real income to the lender (the principal portion just recovers capital already lent) — this mirrors the existing `Abono.interes` precedent.
- Once amortized, a debtor's terms (`monto_total`/`tasa_interes`/`periodo_tasa`/`numero_cuotas`) are correctable later via a dedicated recalculation endpoint, using the exact same algorithm as `concept_service.actualizar_amortizacion`: paid installments are left untouched, unpaid ones are deleted and regenerated from an anchor date, and reducing `numero_cuotas` below what's already paid is rejected.
- `Abono` creation is rejected for an amortized debtor — the two payment-tracking mechanisms are mutually exclusive per debtor, exactly like a `deuda` concept can't mix ad-hoc entries with amortization once amortized.
- Monthly income recognition (`summary_service.py`) is extended so a paid `CuotaDeudor`'s `interes` counts toward `total_ingresos`, keyed by the month it was actually paid (`fecha_pago`) — mirroring how `Abono.interes` is only recognized once actually received, not how concept-side `deuda` entries count planned-but-unpaid amounts (that asymmetry is intentional, see design.md).

## Capabilities

### New Capabilities
None — installment tracking for an amortized debtor is new behavior within the existing `debtor-management` capability, not a separate concern.

### Modified Capabilities
- `debtor-management`: adds amortized debtors (optional interest-rate terms, auto-generated installment schedule, recalculation, and the `Abono`/schedule mutual-exclusivity rule) alongside the existing free-form debtor/abono behavior, which is unchanged for non-amortized debtors.
- `monthly-budget`: the monthly net balance summary's income recognition extends to also include a paid installment's `interes`, alongside the existing abono `interes` recognition.

## Impact

- `app/models/deudor.py`: `Deudor` gains `tasa_interes`, `periodo_tasa`, `numero_cuotas`, `cuota_inicial`; new `CuotaDeudor` table.
- New Alembic migration for the above.
- `app/schemas/deudor.py`: `DeudorCreate`/`DeudorRead` gain amortization fields; new `DeudorAmortizacionUpdate`, `CuotaDeudorRead`, `CuotaDeudorUpdate` schemas.
- `app/services/deudor_service.py`: amortization-aware `create_deudor`, branching `saldo_restante`, new `actualizar_amortizacion`, `create_abono` guard against amortized debtors.
- New `app/services/cuota_deudor_service.py`, mirroring `entry_service.py`'s generation/listing/mark-paid logic for `CuotaDeudor`.
- `app/services/summary_service.py`: income recognition extended to paid `CuotaDeudor.interes`.
- `app/routers/deudores.py`: new `PUT /deudores/{deudor_id}/amortizacion`.
- New `app/routers/cuotas_deudor.py`: `GET /deudores/{deudor_id}/cuotas`, `PATCH /deudores/{deudor_id}/cuotas/{anio}/{mes}`.
- Out of scope: no `.ics` calendar export integration for `CuotaDeudor` (a `Deudor` has no `dia_vencimiento`-equivalent field, and none is added here). No frontend work — that's the sibling change `add-deudor-amortization-ui`, proposed after this one is implemented.
