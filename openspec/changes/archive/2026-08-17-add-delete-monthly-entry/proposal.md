## Why

A month added by mistake (wrong amount, wrong month) can't be removed today - only edited. The user needs a way to undo a mistaken entry, not just correct its values.

## What Changes

- New `DELETE /concepts/{concepto_id}/entries/{anio}/{mes}` removes a single monthly entry, restored to its "no entry" state.
- Only allowed for indefinite recurring concepts (no `duracion_meses`, no amortization data) - deleting one installment out of a generated schedule would leave an incoherent gap.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `monthly-budget`: a monthly entry can be individually deleted, restricted to indefinite recurring concepts.

## Impact

- `app/routers/entries.py`: new `DELETE /{anio}/{mes}` endpoint.
- `app/services/entry_service.py`: new deletion function with the fixed-window guard.
