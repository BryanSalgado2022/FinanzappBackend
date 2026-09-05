## Context

This mirrors the existing `deuda`-type `Concepto` amortization system (`app/models/concepto.py`, `app/services/concept_service.py`, `app/services/entry_service.py`, `app/services/amortization_service.py`) as closely as possible, applied to `Deudor`/`Abono` instead. See proposal.md for motivation. `amortization_service.py`'s pure math functions (`tasa_mensual_desde`, `calcular_cuota_fija`, `generar_tabla_amortizacion`) are entity-agnostic already and are reused completely unchanged.

## Goals / Non-Goals

**Goals:**
- Field-for-field, behavior-for-behavior parity with `Concepto`'s amortization feature, applied to `Deudor`.
- Non-amortized debtors (the overwhelming majority of existing data) see zero behavior change.

**Non-Goals:**
- No `.ics` calendar export integration for the new installment schedule (`Deudor` has no `dia_vencimiento`-equivalent field; out of scope per proposal.md).
- No frontend work (sibling change `add-deudor-amortization-ui`).
- No change to `amortization_service.py` itself.

## Decisions

### New `CuotaDeudor` model, not a reused/generic entry table
`EntradaMensual` is keyed by `concepto_id` with a `(concepto_id, anio, mes)` unique constraint; there is no clean way to make it dual-purpose (`concepto_id` nullable and `deudor_id` nullable, mutually exclusive) without weakening its existing FK/`ondelete=CASCADE` guarantees and complicating every existing query. A parallel model (`CuotaDeudor`, table `cuotas_deudor`, FK `deudor_id → deudores.id, ondelete="CASCADE"`, unique `(deudor_id, anio, mes)`) mirrors `EntradaMensual`'s shape exactly and keeps both tables simple and independently indexed. Alternative considered and rejected: a single polymorphic entries table — adds complexity for no real benefit since the two owning entities (`Concepto`, `Deudor`) never need to be queried together at this granularity.

### `CuotaDeudor.interes`: a field `EntradaMensual` doesn't have
For a `deuda` `Concepto`, the whole installment is an expense regardless of its interest/principal split — no split needs to be stored. For a `Deudor` (the lender), only the interest portion of a received payment is real income; the principal portion just recovers capital already lent — this is the exact reasoning already encoded in `Abono.interes`. Each `CuotaDeudor` row stores its planned `interes` component (taken directly from `amortization_service.generar_tabla_amortizacion`'s per-row `interes` value at generation time), so it can be recognized as income once paid, the same way `Abono.interes` is today.

### Income recognition timing: mirror `Abono`, not `Concepto` entries
`Concepto` entries count toward `total_gastos` whether paid or not (a `monto_planeado` fallback) because an unpaid debt installment is still a real, locked-in obligation for the person who owes it. A `Deudor`'s installment is the opposite direction: the lender has not actually received the interest until the debtor pays. Counting unpaid planned interest as income would overstate the user's real financial position. So `CuotaDeudor.interes` is recognized in `summary_service.py` only when `pagado` is true, keyed by `fecha_pago`'s year/month (mirroring `_sum_abono_interes`'s use of `Abono.fecha`) — never by the installment's own scheduled `anio`/`mes`, which can differ if paid early or late.

### `Abono` and `CuotaDeudor` are mutually exclusive per debtor
Once a debtor has `tasa_interes`/`numero_cuotas` set, `deudor_service.create_abono` raises `ValueError` (→ HTTP 422) rather than silently allowing both tracking mechanisms to coexist and disagree about the remaining balance. This mirrors how an amortized `Concepto` no longer accepts ad-hoc entry upserts outside its generated schedule.

### Recalculation algorithm (mirrors `concept_service.actualizar_amortizacion` exactly)
`n_pagadas = count(CuotaDeudor where pagado)`; `siguiente_numero = (deudor.cuota_inicial or 1) + n_pagadas`. Reject if `numero_cuotas < siguiente_numero - 1`. Anchor date = the month after `max(anio, mes)` among paid installments, or today if none are paid. Delete every unpaid `CuotaDeudor`, update the debtor's terms, and regenerate the schedule from the anchor using the same table-generation function (parameterized by `deudor_id` instead of `concepto_id`), starting at `siguiente_numero`. `cuota_inicial` is never part of this request — it stays permanently locked, exactly as for `Concepto`.

### Schedule anchoring uses `deudor.fecha`, no separate anio/mes param
`ConceptoCreate` accepts an `anio`/`mes` override because a concept can be seeded into a month other than the real current one (e.g. while browsing a future month on the Dashboard). `Deudor` has no such use case — a debtor's `fecha` already represents when the loan started, so the initial schedule is anchored to `fecha`'s own year/month with no additional parameter needed.

### New endpoints mirror the concept-side shape
- `PUT /deudores/{deudor_id}/amortizacion` mirrors `PUT /concepts/{concepto_id}/amortizacion` (same four-field request body, same rejection semantics).
- `GET /deudores/{deudor_id}/cuotas` and `PATCH /deudores/{deudor_id}/cuotas/{anio}/{mes}` are a new nested router (`app/routers/cuotas_deudor.py`), mounted like `entries.py`. `PATCH`, not `PUT`, because every `CuotaDeudor` row is always pre-generated by the schedule — there is no "create from scratch" case, so the request body is just `{ monto_pagado?, pagado }`, not a full upsert. No delete-single-installment endpoint is exposed; every installment is always part of a fixed generated schedule.

## Risks / Trade-offs

- **Duplicated logic between `concept_service.py`/`entry_service.py` and their `Deudor` equivalents.** Accepted: the two entities have different enough surrounding behavior (categories, concept types, `dia_vencimiento`, `duracion_meses` vs. `garantia`, `Abono`) that a shared abstraction would need significant indirection for two call sites. The codebase already tolerates this kind of duplication (e.g. `concept_service._sumar_un_mes` vs. `entry_service._sumar_meses`).
- **Two income-recognition code paths in `summary_service.py` (abono `interes` and installment `interes`) that must stay in sync in spirit.** Mitigated by both being small, well-tested, and reviewed together in this same change.

## Migration Plan

Standard Alembic migration: add nullable columns `tasa_interes`, `periodo_tasa`, `numero_cuotas`, `cuota_inicial` to `deudores`; create `cuotas_deudor` table with its FK and unique constraint. No backfill needed — all existing debtors have these columns null and are entirely unaffected. No rollback complexity beyond the standard downgrade (drop columns/table).
