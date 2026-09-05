## 1. Schema

- [x] 1.1 Add `app/schemas/concepto.py`'s `ConceptoAmortizacionUpdate`: `valor_total: Decimal`, `tasa_interes: Decimal`, `periodo_tasa: PeriodoTasa`, `numero_cuotas: int` — all required together (recalculation always replaces the full term set).

## 2. Service logic

- [x] 2.1 In `app/services/concept_service.py`, add `actualizar_amortizacion(session, user_id, concepto_id, *, valor_total, tasa_interes, periodo_tasa, numero_cuotas) -> tuple[Concepto, int, int, int]`:
  - Fetch the concept (404 via `ConceptoNotFoundError` if not found/not owned).
  - Reject if `concepto.tipo != DEUDA` or `not es_amortizada(concepto)` (no existing amortization to correct).
  - Compute `n_pagadas` and `siguiente_numero` per design.md.
  - Reject if `numero_cuotas < siguiente_numero - 1`.
  - Compute the anchor `(anio_inicio, mes_inicio)` per design.md.
  - Delete every unpaid `EntradaMensual` for this concept.
  - Update `concepto.valor_total`/`tasa_interes`/`periodo_tasa`/`numero_cuotas`, commit, refresh.
  - Return `(concepto, anio_inicio, mes_inicio, siguiente_numero)`.

## 3. Endpoint

- [x] 3.1 Add `PUT /concepts/{id}/amortizacion` in `app/routers/concepts.py`: calls `concept_service.actualizar_amortizacion`, then builds the new table via `generar_tabla_amortizacion`/`tasa_mensual_desde` and calls `entry_service.generar_entradas_amortizacion` with the returned anchor/`cuota_inicial`, mirroring `create_concept`'s existing orchestration. Returns the updated `ConceptoRead` (reusing `_to_read`).
- [x] 3.2 Map `ValueError` from the service to `422`, matching the existing pattern for `create_concept`/`update_concepto`.

## 4. Tests

- [x] 4.1 Add tests: correcting terms on an amortized debt with no paid entries regenerates the whole schedule from today; correcting terms with some paid entries leaves them untouched and regenerates only the unpaid ones, continuing from the month after the last paid one; reducing `numero_cuotas` below what's paid is rejected; attempting recalculation on a non-amortized debt is rejected; attempting it on a non-`deuda` concept is rejected; cross-user scoping (404 for another user's concept).
- [x] 4.2 Run the full test suite and confirm it passes.
