## 1. Ingreso due day

- [x] 1.1 Remove the `ingreso` rejection in `ConceptoCreate.validate_dia_vencimiento` (`app/schemas/concepto.py`)
- [x] 1.2 Remove the equivalent `ingreso` rejection in `concept_service.update_concepto` (`app/services/concept_service.py`)
- [x] 1.3 Update the comment on `Concepto.dia_vencimiento` in `app/models/concepto.py` to reflect it now applies to all three types

## 2. Entry payment date

- [x] 2.1 Add `fecha_pago: date | None` to `EntradaMensual` (`app/models/entrada_mensual.py`)
- [x] 2.2 In `entry_service._save_entry`, set `fecha_pago = date.today()` when `pagado` transitions from false to true, and clear it to `None` when `pagado` is false (checked against the entry's prior value, not overwriting an unchanged paid entry's existing date)
- [x] 2.3 Add `fecha_pago` to `EntradaMensualRead` (`app/schemas/entrada_mensual.py`)

## 3. Concept and debtor finish date

- [x] 3.1 Add `finalizado_en: date | None` to `Concepto` (`app/models/concepto.py`) and `Deudor` (`app/models/deudor.py`)
- [x] 3.2 In `concept_service.update_concepto`, set `finalizado_en = date.today()` when `activo` transitions to `False`, clear it to `None` when it transitions to `True`
- [x] 3.3 In `deudor_service.update_deudor`, same transition logic as 3.2
- [x] 3.4 Add `finalizado_en` to `ConceptoRead` (`app/schemas/concepto.py`) and `DeudorRead` (`app/schemas/deudor.py`)

## 4. Migration

- [x] 4.1 Generate one combined Alembic migration for all three new nullable columns (`concepts.dia_vencimiento` unchanged, `monthly_entries.fecha_pago`, `concepts.finalizado_en`, `deudores.finalizado_en`) and review it before applying

## 5. Tests

- [x] 5.1 Update/replace the existing test(s) asserting `dia_vencimiento` is rejected for `ingreso` with tests confirming it's now accepted (create and update paths)
- [x] 5.2 `tests/test_entries_summary.py` or a new test: marking an entry paid sets `fecha_pago` to today; re-saving an already-paid entry without changing `pagado` leaves `fecha_pago` unchanged; marking it unpaid clears `fecha_pago`
- [x] 5.3 `tests/test_concepts.py`: marking a concept `activo: false` sets `finalizado_en`; reactivating it clears `finalizado_en`
- [x] 5.4 `tests/test_deudores.py`: same transition test as 5.3, for `Deudor`

## 6. Docs

- [x] 6.1 Add a "Decisiones clave a recordar" bullet to `README.md` documenting `fecha_pago`/`finalizado_en` and why `dia_vencimiento` now applies to all three concept types
