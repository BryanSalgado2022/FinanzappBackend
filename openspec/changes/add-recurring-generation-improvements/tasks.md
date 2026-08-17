## 1. Data model and migration

- [x] 1.1 Add nullable `cuota_inicial: int | None` to `Concepto` in `app/models/concepto.py`, with a comment noting it's amortization-only and immutable
- [x] 1.2 Generate and write an Alembic migration adding the `cuota_inicial` column to `concepts`
- [x] 1.3 Apply the migration against the docker compose `db` service

## 2. Schemas and validation

- [x] 2.1 Add `cuota_inicial: int | None = Field(default=None, ge=1)` to `ConceptoCreate` in `app/schemas/concepto.py`
- [x] 2.2 Add a `validate_cuota_inicial` model validator to `ConceptoCreate`: reject if set without amortization data (`tasa_interes`+`numero_cuotas`), reject if `cuota_inicial > numero_cuotas`
- [x] 2.3 Add `cuota_inicial: int | None = None` to `ConceptoUpdate` (accepted only so it can be explicitly rejected downstream)
- [x] 2.4 Add `cuota_inicial: int | None` to `ConceptoRead`

## 3. Service layer: cuota_inicial

- [x] 3.1 Add `cuota_inicial` parameter to `concept_service.create_concepto`, passed through to the `Concepto` constructor
- [x] 3.2 In `concept_service.update_concepto`, unconditionally reject `cuota_inicial` when provided, with the descriptive message from design.md
- [x] 3.3 Add `generar_entradas_amortizacion`'s `cuota_inicial: int = 1` parameter and updated offset logic per design.md, in `app/services/entry_service.py`
- [x] 3.4 Add `concept_service.valor_total_efectivo(concepto)` per design.md
- [x] 3.5 Update `concept_service.saldo_restante` to use `valor_total_efectivo(concepto)` instead of `concepto.valor_total` directly

## 4. Service layer: lazy year-extension

- [x] 4.1 Add `entry_service.asegurar_entradas_anio_actual(session, concepto)` per design.md

## 5. Routers

- [x] 5.1 Pass `payload.cuota_inicial` through in `create_concept` (`app/routers/concepts.py`), and pass it to `generar_entradas_amortizacion` when amortized
- [x] 5.2 Add `cuota_inicial=concepto.cuota_inicial` to `_to_read`
- [x] 5.3 Pass `payload.cuota_inicial` through in `update_concept`
- [x] 5.4 Call `entry_service.asegurar_entradas_anio_actual(session, concepto)` in `list_entries` (`app/routers/entries.py`), before fetching the entries to return

## 6. Tests

- [x] 6.1 Test creating an amortized debt with `cuota_inicial` generates entries only from that installment onward, landing in the creation month
- [x] 6.2 Test creating an amortized debt without `cuota_inicial` behaves exactly as before (starts at installment 1)
- [x] 6.3 Test `saldo_restante` for a debt with `cuota_inicial > 1` reflects the schedule's balance at that starting point, not the full `valor_total`
- [x] 6.4 Test rejecting `cuota_inicial` on a non-amortized concept
- [x] 6.5 Test rejecting `cuota_inicial` outside 1..numero_cuotas
- [x] 6.6 Test rejecting a PATCH attempt to change `cuota_inicial`, with a descriptive error message
- [x] 6.7 Test that viewing an indefinite recurring concept's entries with a gap at the real current month generates entries through December using the most recent entry's amount
- [x] 6.8 Test that existing entries are never overwritten by the year-extension
- [x] 6.9 Test that a concept with no entries at all triggers no generation
- [x] 6.10 Test that amortized and fixed-duration concepts never trigger the year-extension behavior
- [x] 6.11 Run the full test suite inside the `api` container and confirm all tests pass

## 7. Manual verification

- [x] 7.1 Restart the `api` container so the code changes take effect
- [x] 7.2 Verify via API: create an amortized debt with `cuota_inicial` set, confirm entries and `saldo_restante` reflect the starting point
- [x] 7.3 Verify via API: manually backdate an indefinite recurring concept's latest entry to a prior year in the test database, then GET its entries and confirm the current year gets filled
