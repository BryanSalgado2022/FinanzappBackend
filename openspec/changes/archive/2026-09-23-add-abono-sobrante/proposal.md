## Why

The user reported a real case: an amortized debtor paid 200.000 when her planned cuota was 148.757. Today there is no way to even record that — `PATCH /deudores/{id}/cuotas/{anio}/{mes}` accepts any `monto_pagado`, but nothing routes the surplus anywhere; it silently sits in that one installment's `monto_pagado`, quietly shrinking the balance without ever recalculating the remaining schedule (an implicit, un-reflected "reducir plazo"). The already-shipped `add-abono-capital` gives a manual way to record a principal prepayment for `Deudor`, but the user has to compute the surplus by hand and register it separately. `Concepto` (the user's own debts) doesn't even have that manual mechanism yet.

## What Changes

- `Deudor`: `PATCH /deudores/{id}/cuotas/{anio}/{mes}` gains an optional `abono_capital_modo` field. When provided alongside a `monto_pagado` that exceeds the installment's `monto_planeado`, the endpoint caps the installment's stored `monto_pagado` to `monto_planeado` and routes the excess into the existing `registrar_abono_capital` mechanism, in one request. Omitting the field leaves today's behavior completely unchanged.
- `Concepto`: gets the underlying principal-prepayment mechanism for the first time (`registrar_abono_capital` equivalent, mirroring `Deudor`'s — reducir_plazo/reducir_cuota, full settlement closes the concept, `cuota_fija` becomes schedule-derived instead of terms-derived). Scoped to only what the surplus-routing flow needs — no standalone manual endpoint is added beyond that.
- `Concepto`: `PUT /concepts/{id}/entries/{anio}/{mes}` gains the same optional `abono_capital_modo` field, with the same capping/excess logic as `Deudor`'s.
- Partial payments (monto_pagado < monto_planeado) are explicitly out of scope — stored as-is, exactly like today.
- A sibling frontend change will follow (not part of this change): an expandable row for entering the paid amount (mirroring `MonthEntryRow`'s existing pattern) on both `DeudorDetail`'s cronograma and `ConceptDetail`'s entries, with inline surplus detection and modo selection, no extra confirmation step.

## Capabilities

### New Capabilities
(none — this extends existing capabilities)

### Modified Capabilities
- `debtor-management`: adds routing a payment surplus into a principal prepayment when marking an installment paid.
- `budget-concepts`: adds the principal-prepayment mechanism for amortized debts (new for `Concepto`), mirroring `Deudor`'s.
- `monthly-budget`: adds routing a payment surplus into a principal prepayment when marking a monthly entry paid.

## Impact

- `app/schemas/deudor.py`: `CuotaDeudorUpdate` gains `abono_capital_modo: ModoAbonoCapital | None`.
- `app/services/deudor_service.py`: new orchestration function combining `cuota_deudor_service.marcar_pagada` (capped) and `registrar_abono_capital` (excess).
- `app/routers/cuotas_deudor.py`: `mark_cuota` branches on `abono_capital_modo`.
- `app/schemas/entrada_mensual.py`: `EntradaMensualUpsert` gains `abono_capital_modo: ModoAbonoCapital | None`.
- `app/models/concepto.py` or a new model file: new table for Concepto's capital-prepayment ledger (no `es_abono_capital`-style flag needed — every row is by definition a prepayment, unlike `Deudor`'s `Abono` which also carries unrelated historical records).
- `app/services/concept_service.py`: `cuota_fija` becomes schedule-derived (takes `session` now); `saldo_restante` adds the new ledger's sum; new `registrar_abono_capital`.
- `app/routers/entries.py`: `upsert_entry` branches on `abono_capital_modo`.
- `app/services/entry_service.py`: orchestration mirroring the Deudor side.
- New Alembic migration for the Concepto capital-prepayment table.
