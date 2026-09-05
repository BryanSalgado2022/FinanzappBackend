## Why

Setting up an amortized debt requires filling in several fields (amount, rate, period, installment count). Today, none of them can be corrected afterward — the only path is deleting the concept and recreating it from scratch, which the user reported as uncomfortable for fixing a small mistake.

## What Changes

- Add a dedicated recalculation endpoint letting a user correct `valor_total`, `tasa_interes`, `periodo_tasa`, and `numero_cuotas` on an already-amortized debt. `cuota_inicial` stays permanently immutable, unchanged from today.
- Already-paid monthly entries are never touched — they keep their original `monto_planeado`/`monto_pagado`/`fecha_pago` exactly as recorded. Every not-yet-paid entry is deleted and regenerated from a freshly computed amortization table using the new terms, continuing the calendar sequence from the month after the last paid entry (or from today, if nothing has been paid yet).
- Rejects the request if the new `numero_cuotas` would be fewer than the installments already paid — there's no coherent schedule that fits.

## Capabilities

### Modified Capabilities
- `budget-concepts`: "Financial terms are immutable once amortization data exists" changes to allow `valor_total`/`tasa_interes`/`periodo_tasa`/`numero_cuotas` to be corrected via the new recalculation path, while `cuota_inicial` remains locked exactly as before.
- `monthly-budget`: gains the recalculation's entry-regeneration behavior (delete-and-regenerate unpaid entries, paid entries untouched) as a new documented case alongside the existing auto-generation requirements.

## Impact

- `app/services/concept_service.py`: new `actualizar_amortizacion(session, concepto, *, valor_total, tasa_interes, periodo_tasa, numero_cuotas)` — validates preconditions, deletes unpaid entries, updates the concept's fields, and returns the info needed to regenerate entries (continuation anchor date, starting installment number).
- `app/routers/concepts.py`: new endpoint (e.g. `PUT /concepts/{id}/amortizacion`) orchestrating `concept_service.actualizar_amortizacion` + `entry_service.generar_entradas_amortizacion`, mirroring how `create_concept` already orchestrates the same two services.
- No change to `update_concepto`/`ConceptoUpdate` (the existing simple-field PATCH) — this is a separate, dedicated path given its different semantics (destructive regeneration vs. a plain field update).
