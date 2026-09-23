## 1. Concepto: principal-prepayment mechanism (new)

- [x] 1.1 Add `app/models/abono_capital_concepto.py`: `AbonoCapitalConcepto(SQLModel, table=True)` with `__tablename__ = "abonos_capital_conceptos"`, `{ id, concepto_id: int (foreign_key="concepts.id", index=True), monto: Decimal, fecha: date }`. Register it in `app/models/__init__.py` alongside the other models.
- [x] 1.2 Generate and hand-review the Alembic migration for the new table (brand new table, no existing rows — no `server_default` concern). Apply via `docker compose exec api alembic upgrade head`.
- [x] 1.3 In `app/schemas/concepto.py` (or wherever fits best), reuse `ModoAbonoCapital` from `app/schemas/deudor.py` (import it, do not redefine) for the new Concepto request schema.
- [x] 1.4 In `app/services/concept_service.py`, change `cuota_fija(concepto)` to `cuota_fija(session: Session, concepto: Concepto) -> Decimal | None`: read the next not-yet-paid `EntradaMensual.monto_planeado` for that concept, falling back to the most recent entry, falling back to the stored-terms computation if no entries exist. Update every call site (routers, `_to_read`) to pass `session`.
- [x] 1.5 Change `concept_service.saldo_restante` to also subtract `sum(AbonoCapitalConcepto.monto)` for that concept, unconditionally (no flag needed — see design.md).
- [x] 1.6 Add `concept_service.registrar_abono_capital(session, user_id, concepto_id, *, monto, fecha, modo) -> Concepto`, a straight port of `deudor_service.registrar_abono_capital`: rejects non-amortized (422), creates the `AbonoCapitalConcepto` row, recomputes `saldo_restante`; if `<= 0`, deletes unpaid `EntradaMensual` rows and finalizes (`activo=False`, `finalizado_en=today()`); otherwise computes the new `numero_cuotas_restantes` (via `calcular_cuotas_restantes` for `reducir_plazo`, unchanged count for `reducir_cuota`), updates `concepto.numero_cuotas` (never `valor_total`), regenerates the remaining schedule via `generar_tabla_amortizacion` + the existing entry-generation helper.

## 2. Concepto: expose the new mechanism via the surplus-routing flow

- [x] 2.1 In `app/schemas/entrada_mensual.py`, add `abono_capital_modo: ModoAbonoCapital | None = None` to `EntradaMensualUpsert`.
- [x] 2.2 In `app/services/entry_service.py`, add an orchestration function (or extend `upsert_monthly_entry`) that, when `abono_capital_modo` is given: rejects (422) if the concept isn't amortized or if `monto_pagado` doesn't exceed `monto_planeado`; otherwise upserts the entry with `monto_pagado` capped to `monto_planeado`, then calls `concept_service.registrar_abono_capital` with the excess and the chosen mode. When no mode is given, behavior is unchanged from today.
- [x] 2.3 In `app/routers/entries.py`, wire `upsert_entry` to call the extended logic when `payload.abono_capital_modo` is set.

## 3. Deudor: expose the surplus-routing flow (extends already-shipped machinery)

- [x] 3.1 In `app/schemas/deudor.py`, add `abono_capital_modo: ModoAbonoCapital | None = None` to `CuotaDeudorUpdate`.
- [x] 3.2 In `app/services/deudor_service.py`, add an orchestration function that, when `abono_capital_modo` is given: rejects (422) if the debtor isn't amortized or if `monto_pagado` doesn't exceed the cuota's `monto_planeado`; otherwise calls `cuota_deudor_service.marcar_pagada` with `monto_pagado` capped to `monto_planeado`, then calls the existing `registrar_abono_capital` unchanged with the excess and the chosen mode, using the cuota's `fecha_pago` as the prepayment's `fecha`. When no mode is given, behavior is unchanged from today (existing `marcar_pagada` call, unmodified).
- [x] 3.3 In `app/routers/cuotas_deudor.py`, wire `mark_cuota` to call the extended logic when `payload.abono_capital_modo` is set.

## 4. Tests

- [x] 4.1 Concepto prepayment mechanism (mirrors `tests/test_abono_capital.py`): reducir_plazo/reducir_cuota, already-paid entries untouched, full prepayment finalizes, rejected on non-amortized, reducir_plazo rejected when installment doesn't cover interest, `valor_total` unchanged, cross-user 404.
- [x] 4.2 Deudor surplus routing: surplus correctly capped+routed for both modes; no mode → unchanged existing behavior (regression check against `PaymentPriorityCard`'s "Pagar mes" shape: `monto_pagado=monto_planeado, pagado=true`, no mode); rejected when no surplus; rejected on non-amortized.
- [x] 4.3 Concepto surplus routing: same coverage as 4.2, adapted for entries.
- [x] 4.4 Confirm existing `cuota_fija`/`saldo_restante` tests for Concepto (creation, correction, activation) still pass unchanged.
- [x] 4.5 Run the full backend test suite and confirm everything passes.
