## Why

There's no way to add amortization terms (tasa_interes/periodo_tasa/numero_cuotas) to a `Concepto` (deuda) or `Deudor` that was created without them — only creation-time, or correcting an already-amortized one. Today the only workaround is delete-and-recreate, losing all history. The user hit this directly with an existing debtor and confirmed the same gap applies to their own debts.

## What Changes

- New `POST /concepts/{concepto_id}/amortizacion` and `POST /deudores/{deudor_id}/amortizacion` endpoints (distinct from the existing `PUT` correction endpoints) that set amortization terms for the first time on an entity that doesn't yet have them.
- Any not-yet-paid monthly entry / scheduled installment is replaced by a freshly generated schedule anchored at today; already-paid ones are left untouched as historical record. The user supplies `valor_total`/`monto_total` and an optional `cuota_inicial` to reflect where they really are — mirrors the existing "already partway through this loan" mechanism at creation time. No automatic reconciliation against prior abonos/payments is attempted.
- Rejected (422) if the entity already has amortization data (use the correction endpoint instead), or — for concepts — isn't of type `deuda`.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `budget-concepts`: adds a way to set amortization terms on an existing non-amortized debt concept, alongside the existing creation-time and correction paths.
- `debtor-management`: adds a way to set amortization terms on an existing non-amortized debtor, alongside the existing creation-time and correction paths.

## Impact

- `app/schemas/concepto.py`: new `ConceptoAmortizacionActivar`.
- `app/schemas/deudor.py`: new `DeudorAmortizacionActivar`.
- `app/services/concept_service.py`: new `activar_amortizacion`.
- `app/services/deudor_service.py`: new `activar_amortizacion`.
- `app/routers/concepts.py`: new `POST /concepts/{concepto_id}/amortizacion`.
- `app/routers/deudores.py`: new `POST /deudores/{deudor_id}/amortizacion`.
- No changes to `saldo_restante`/`cuota_fija`/`valor_total_efectivo`/`monto_total_efectivo` in either service — they already branch correctly once the fields are set.
