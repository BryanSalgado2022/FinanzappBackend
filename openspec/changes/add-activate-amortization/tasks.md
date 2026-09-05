## 1. Schemas

- [x] 1.1 In `app/schemas/concepto.py`, add `ConceptoAmortizacionActivar { valor_total: Decimal, tasa_interes: Decimal, periodo_tasa: PeriodoTasa, numero_cuotas: int, cuota_inicial: int | None = Field(default=None, ge=1) }`, with a validator rejecting `cuota_inicial > numero_cuotas` (mirrors `ConceptoCreate`).
- [x] 1.2 In `app/schemas/deudor.py`, add `DeudorAmortizacionActivar { monto_total: Decimal, tasa_interes: Decimal, periodo_tasa: PeriodoTasa, numero_cuotas: int, cuota_inicial: int | None = Field(default=None, ge=1) }`, same validator.

## 2. Service logic

- [x] 2.1 In `app/services/concept_service.py`, add `activar_amortizacion(session, user_id, concepto_id, *, valor_total, tasa_interes, periodo_tasa, numero_cuotas, cuota_inicial)`: fetch concepto (404 via `ConceptoNotFoundError`), reject if `tipo != TipoConcepto.DEUDA` or `es_amortizada(concepto)` already true (`ValueError`), delete every not-yet-paid `EntradaMensual`, set the fields + `cuota_inicial`, commit, then compute the table and call `entry_service.generar_entradas_amortizacion` anchored at `date.today()`'s year/month with `cuota_inicial=cuota_inicial or 1`.
- [x] 2.2 Mirror the same in `app/services/deudor_service.py`: `activar_amortizacion(session, user_id, deudor_id, *, monto_total, tasa_interes, periodo_tasa, numero_cuotas, cuota_inicial)`, deleting not-yet-paid `CuotaDeudor` rows and generating via `cuota_deudor_service.generar_cuotas_amortizacion`.

## 3. Routers

- [x] 3.1 In `app/routers/concepts.py`, add `POST /concepts/{concepto_id}/amortizacion` calling `concept_service.activar_amortizacion`, mirroring `update_amortizacion`'s error handling (404 on not found, 422 on `ValueError`).
- [x] 3.2 In `app/routers/deudores.py`, add `POST /deudores/{deudor_id}/amortizacion` calling `deudor_service.activar_amortizacion`, same error handling.

## 4. Tests

- [x] 4.1 Add concept activation tests: success generates schedule anchored at today; already-paid entries preserved; not-yet-paid entries replaced; `cuota_inicial` respected; rejected when already amortized; rejected on non-`deuda` type; cross-user 404 scoping.
- [x] 4.2 Add debtor activation tests: same coverage, plus confirming existing abonos are left untouched and no longer feed `saldo_restante` once activated.
- [x] 4.3 Run the full backend test suite and confirm everything passes.
