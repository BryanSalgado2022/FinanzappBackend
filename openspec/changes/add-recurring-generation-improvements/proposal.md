## Why

Two gaps surfaced from real usage: (1) a debt the user already had before adopting the app always generates its amortization schedule starting at installment 1, with no way to say "I'm already on installment N" for a credit with prior real-world payments; (2) an indefinite recurring concept (salary, rent) only has entries generated through December of its creation year, requiring one manual edit each January to extend into the new year.

## What Changes

- Debts with amortization gain an optional `cuota_inicial` (starting installment number). Entries are only generated from that installment onward; the remaining balance reflects the schedule's balance at that point instead of the full `valor_total`. Optional, defaults to installment 1 (no behavior change). Immutable after creation, like the other amortization terms, with a descriptive rejection message.
- Indefinite recurring concepts (no `duracion_meses`, not amortized) that are missing an entry for the real current month now auto-generate the rest of the current year - lazily, the next time their entries are listed, using the most recently known planned amount. No scheduler/cron involved.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `budget-concepts`: debts gain an optional, immutable starting-installment field; the remaining-balance and immutability requirements account for it.
- `monthly-budget`: indefinite recurring concepts auto-extend into a new calendar year on demand instead of requiring a manual edit; the amortized-debt generation requirement accounts for a starting installment.

## Impact

- `app/models/concepto.py`: new nullable `cuota_inicial` column.
- `alembic/versions/`: new migration.
- `app/schemas/concepto.py`: `ConceptoCreate` validation (amortization-only, 1..numero_cuotas); `ConceptoUpdate` gains the field solely to reject it with a clear message; `ConceptoRead` gains the field.
- `app/services/amortization_service.py` / `entry_service.py`: schedule generation honors a starting installment; new lazy year-extension logic.
- `app/services/concept_service.py`: `saldo_restante` accounts for a starting installment; `update_concepto` rejects `cuota_inicial` changes.
- `app/routers/concepts.py`, `app/routers/entries.py`: wire the above through.
