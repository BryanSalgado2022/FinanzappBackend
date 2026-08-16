## Why

Debts and fixed expenses have a real due date each month (e.g. "this installment is due on the 15th"), but the system has no way to record it. The user has no way to see, at a glance, which unpaid monthly entries are actually overdue versus simply not yet due.

## What Changes

- Add an optional `dia_vencimiento` field (1-28) to `Concepto`, valid only for `deuda` and `gasto_fijo` concepts.
- Allow `dia_vencimiento` to be set at creation and updated at any time via `PATCH /concepts/{id}` — unlike the amortization terms, it does not trigger any recalculation, so it is exempt from the project's "financial terms are immutable" convention.
- Return `dia_vencimiento` on `ConceptoRead`.
- Compute and return a `vencida` (overdue) flag on each monthly entry, true when the entry is unpaid and its computed due date (the concept's `dia_vencimiento` combined with the entry's `anio`/`mes`) has passed.
- Reject `dia_vencimiento` outside the 1-28 range, and reject it entirely on `ingreso` concepts.

Out of scope: any UI changes (separate frontend change), due-date reminders/notifications, an "upcoming due dates" view.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `budget-concepts`: concepts of type `deuda`/`gasto_fijo` gain an optional, mutable `dia_vencimiento` field.
- `monthly-budget`: monthly entries gain a computed `vencida` (overdue) flag.

## Impact

- `app/models/concepto.py`: new nullable `dia_vencimiento` column.
- `alembic/versions/`: new migration adding the column.
- `app/schemas/concepto.py`: `ConceptoCreate`, `ConceptoUpdate`, `ConceptoRead` gain `dia_vencimiento`; new validator for the 1-28 range and the `ingreso` rejection.
- `app/schemas/entrada_mensual.py`: `EntradaMensualRead` gains `vencida`.
- `app/services/concept_service.py`: `create_concepto`/`update_concepto` accept `dia_vencimiento`.
- `app/routers/concepts.py`, `app/routers/entries.py`: construct the new fields in their read schemas.
- Existing tests in `tests/test_concepts.py` and a new overdue-flag test file.
