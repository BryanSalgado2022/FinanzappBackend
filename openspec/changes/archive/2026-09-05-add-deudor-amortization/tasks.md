## 1. Model and migration

- [x] 1.1 Add `tasa_interes` (`Decimal`, max_digits=7, decimal_places=4, nullable), `periodo_tasa` (reuse `PeriodoTasa` from `app/models/concepto.py`, nullable), `numero_cuotas` (int, nullable), `cuota_inicial` (int, nullable) to `Deudor` in `app/models/deudor.py`.
- [x] 1.2 Add `CuotaDeudor` model (table `cuotas_deudor`) to `app/models/deudor.py`: `id`, `deudor_id` (FK `deudores.id`, index, `ondelete="CASCADE"`), `anio`, `mes`, `monto_planeado`, `monto_pagado` (nullable), `pagado` (bool, default False), `fecha_pago` (nullable), `interes` (nullable Decimal), `created_at`. Unique constraint on `(deudor_id, anio, mes)`.
- [x] 1.3 Generate and apply an Alembic migration for the above (nullable columns + new table, no backfill).

## 2. Schemas

- [x] 2.1 In `app/schemas/deudor.py`, add the four amortization fields to `DeudorCreate` with the same `model_validator` rules as `ConceptoCreate` (tasa_interes+numero_cuotas together, periodo_tasa defaults to mensual, cuota_inicial requires both and cannot exceed numero_cuotas).
- [x] 2.2 Add `tasa_interes`, `periodo_tasa`, `numero_cuotas`, `cuota_inicial`, `cuota_fija` (computed, nullable) to `DeudorRead`.
- [x] 2.3 Add `DeudorAmortizacionUpdate` (valor_total→`monto_total`, tasa_interes, periodo_tasa, numero_cuotas, all required together), mirroring `ConceptoAmortizacionUpdate`.
- [x] 2.4 Add `CuotaDeudorRead` (id, deudor_id, anio, mes, monto_planeado, monto_pagado, pagado, fecha_pago, interes) and `CuotaDeudorUpdate` (monto_pagado optional, pagado required) to a new or existing schema module (e.g. extend `app/schemas/deudor.py`).

## 3. Service logic

- [x] 3.1 In `app/services/deudor_service.py`, add `es_amortizada(deudor)` mirroring `concept_service.es_amortizada`.
- [x] 3.2 Extend `create_deudor` to accept the four amortization params; when amortization is set, compute the schedule via `amortization_service` functions and generate installments (anchored to `deudor.fecha`'s year/month) using the new cuota generation helper (task 4.2).
- [x] 3.3 Branch `saldo_restante`: amortized debtors compute from `monto_total` (adjusted for `cuota_inicial` if >1, mirroring `concept_service.valor_total_efectivo`) minus the sum of `CuotaDeudor.monto_pagado`; non-amortized debtors keep the exact current abono-sum computation unchanged.
- [x] 3.4 Add `cuota_fija(deudor)` mirroring `concept_service.cuota_fija`.
- [x] 3.5 Guard `create_abono` to raise `ValueError` when `es_amortizada(deudor)` is true.
- [x] 3.6 Add `actualizar_amortizacion(session, user_id, deudor_id, *, monto_total, tasa_interes, periodo_tasa, numero_cuotas)` mirroring `concept_service.actualizar_amortizacion`'s algorithm exactly (paid installments untouched, unpaid deleted and regenerated from the anchor date, `numero_cuotas` reduction below paid count rejected), returning what the router needs to call the generation helper.

## 4. New `cuota_deudor_service.py`

- [x] 4.1 Create `app/services/cuota_deudor_service.py` with `get_cuota`, `list_cuotas` (ordered by anio, mes), mirroring `entry_service.py`'s equivalents but keyed by `deudor_id`.
- [x] 4.2 Add `generar_cuotas_amortizacion(session, deudor, tabla, anio_inicio, mes_inicio, cuota_inicial=1)` mirroring `entry_service.generar_entradas_amortizacion`, additionally copying each table row's `interes` value onto the created `CuotaDeudor`. Never overwrites an existing row for the same `(deudor_id, anio, mes)`.
- [x] 4.3 Add `marcar_pagada(session, deudor, anio, mes, *, monto_pagado, pagado)` to update an existing `CuotaDeudor`'s `monto_pagado`/`pagado`, setting `fecha_pago` to today only on the paid transition and clearing it when marked unpaid (mirrors `entry_service._save_entry`'s pagado-transition logic). Raise `EntryNotFoundError`-equivalent if the installment doesn't exist for that anio/mes.

## 5. Routers

- [x] 5.1 In `app/routers/deudores.py`, wire `create_deudor`'s new params through from `DeudorCreate`, include the new read fields in `_to_read`, and add `PUT /deudores/{deudor_id}/amortizacion` calling `deudor_service.actualizar_amortizacion` then `cuota_deudor_service.generar_cuotas_amortizacion`, mirroring `concepts.py`'s `update_amortizacion` endpoint (404 on not found, 422 on `ValueError`).
- [x] 5.2 Create `app/routers/cuotas_deudor.py` (prefix `/deudores/{deudor_id}/cuotas`, tags `["cuotas-deudor"]`) with `GET ""` (list) and `PATCH "/{anio}/{mes}"` (mark paid), mirroring `entries.py`'s structure minus the delete endpoint and minus `asegurar_entradas_anio_actual` (not applicable - installments are always fully pre-generated).
- [x] 5.3 Register the new router in `app/main.py`.

## 6. Monthly income recognition

- [x] 6.1 In `app/services/summary_service.py`, add a `_sum_cuota_deudor_interes(session, user_id, anio, mes)` mirroring `_sum_abono_interes` but summing `CuotaDeudor.interes` where `pagado` is true and `fecha_pago`'s year/month match, joined through `Deudor` for `user_id` scoping.
- [x] 6.2 Add that sum into `monthly_summary`'s `total_ingresos` alongside the existing abono interest sum.

## 7. Tests

- [x] 7.1 Add debtor-creation tests: amortized debtor generates its schedule with the correct fixed installment; tasa_interes/numero_cuotas-together validation; cuota_inicial validation; non-amortized debtor unaffected (mirror the equivalent `Concepto` creation tests).
- [x] 7.2 Add installment tests: listing, marking paid (amount + date recorded), marking unpaid (date cleared), cross-user 404 scoping.
- [x] 7.3 Add `saldo_restante`/`cuota_fija` tests for amortized debtors, and confirm non-amortized `saldo_restante` behavior is byte-for-byte unchanged.
- [x] 7.4 Add `create_abono` rejection test for amortized debtors.
- [x] 7.5 Add recalculation tests mirroring `tests/test_edit_amortized_debt.py`: paid installments preserved, regeneration from anchor, `numero_cuotas` reduction rejected, rejection on non-amortized debtor, cross-user 404.
- [x] 7.6 Add `monthly_summary` tests: paid installment interest counted in the month of `fecha_pago` (not the installment's own scheduled month), unpaid installments have no effect, principal has no effect.
- [x] 7.7 Run the full backend test suite and confirm everything passes.
