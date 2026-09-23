## Context

See proposal.md for motivation. This builds directly on `add-abono-capital` (already shipped for `Deudor`: `deudor_service.registrar_abono_capital`, `ModoAbonoCapital`, `amortization_service.calcular_cuotas_restantes`) and reuses that machinery unchanged rather than redesigning it. `Concepto` has no principal-prepayment mechanism at all today, so this change ports it there for the first time, then adds the surplus-routing behavior on top for both entities.

## Goals / Non-Goals

**Goals:**
- Let a surplus payment on a `Deudor` installment or `Concepto` monthly entry be routed into a principal prepayment in one request, reusing the existing `reducir_plazo`/`reducir_cuota` mechanism.
- Give `Concepto` the underlying prepayment mechanism it's missing, scoped to only what the surplus flow needs.
- Never double-count a surplus in either entity's remaining-balance calculation.

**Non-Goals:**
- Partial payments (monto_pagado < monto_planeado) — out of scope, unchanged.
- A standalone manual "abono a capital" endpoint/UI for `Concepto` — only the mechanism the surplus flow calls is built; no dedicated manual-entry requirement.
- Any frontend work — a sibling `add-abono-sobrante-ui` change follows this one.

## Decisions

### The cuota/entry's `monto_pagado` is always capped to the planned amount when a mode is given; only the excess becomes the prepayment
`saldo_restante` for both entities sums two things once amortized: paid installments/entries, and recorded prepayments. If the full 200.000 were stored as `monto_pagado` on the installment *and* a 51.243 prepayment were also created, the balance would drop by 251.243 instead of 200.000. So whenever `abono_capital_modo` is provided, the installment/entry's stored `monto_pagado` is always the *planned* amount (never the amount the caller sent), and the prepayment is always exactly `monto_pagado_solicitado - monto_planeado`. When no mode is given, behavior is 100% unchanged — any `monto_pagado` is stored as-is, matching every existing caller (e.g. the Dashboard's "Pagar mes" quick action, which never sends a mode).

### Single endpoint per entity does both steps, not two frontend calls
`PATCH /deudores/{id}/cuotas/{anio}/{mes}` and `PUT /concepts/{id}/entries/{anio}/{mes}` each gain the optional field and internally call two existing/mirrored service functions in sequence within the same request (mark-paid-capped, then register the prepayment). This isn't a single DB transaction — both this codebase's existing services already commit in multiple steps (`registrar_abono_capital` itself does two commits) — but it removes the frontend-visible failure window between "cuota shows paid" and "prepayment recorded" that two separate API calls would have.

### `Concepto`'s new prepayment ledger needs no `es_abono_capital`-style flag
`Deudor.saldo_restante` needed that flag because `Abono` already existed as a free-form ledger *before* `add-abono-capital`, and rows recorded before a debtor was amortized had to be excluded (per `add-activate-amortization`) from ever feeding the balance again. `Concepto.saldo_restante` has no equivalent history problem: it already sums every `EntradaMensual.monto_pagado` unconditionally, activation-time or not (that was already the design in `add-activate-amortization` for `Concepto`). The new table introduced here is created solely for this feature, has no pre-existing rows, and every row in it is by definition a capital prepayment — so `saldo_restante` can just add its full sum, unconditionally, with no flag.

New model: `AbonoCapitalConcepto` (`app/models/abono_capital_concepto.py`, table `abonos_capital_conceptos`) — `{ id, concepto_id, monto: Decimal, fecha: date }`. No `interes` field (mirrors `AbonoCapitalCreate`'s shape for `Deudor`, which is also pure-principal by definition).

### `Concepto.cuota_fija` becomes schedule-derived (takes `session` now)
Exactly the same problem `add-abono-capital` already solved for `Deudor`: `cuota_fija` is currently `calcular_cuota_fija(valor_total, tasa, numero_cuotas)` — a stored-terms recomputation that assumes those three fields alone describe one coherent fixed-payment table for the debt's entire life. That stops being true the moment `numero_cuotas` can move independently of `valor_total` after a prepayment. The new definition reads the next not-yet-paid `EntradaMensual.monto_planeado` (falling back to the most recent entry, or the stored-terms computation if no schedule exists yet) — identical port of `deudor_service.cuota_fija`'s already-shipped logic. Every existing call site is updated to pass `session`.

### `Concepto.registrar_abono_capital` is a straight port of `deudor_service.registrar_abono_capital`
Same reducir_plazo/reducir_cuota branching via the already-shipped, entity-agnostic `amortization_service.calcular_cuotas_restantes`/`generar_tabla_amortizacion`. Full settlement sets `activo=False`/`finalizado_en=today()` (the same fields `Deudor` uses, already present on `Concepto`) and clears not-yet-paid entries, mirroring `Deudor`'s transition exactly.

## Risks / Trade-offs

- **`concept_service.cuota_fija`'s signature changes** (now takes `session`) — every call site must be updated. Mitigated the same way the Deudor port was: the new definition is provably identical to the old one in every scenario that predates this change.
- **Two entities now each have their own principal-prepayment implementation** (`Deudor`'s from `add-abono-capital`, `Concepto`'s new here) rather than one shared abstraction. Accepted: the two entities' underlying storage (`Abono` vs. the new `AbonoCapitalConcepto`) and balance-calculation history differ enough (see the `es_abono_capital` decision above) that a shared abstraction would add indirection without removing real duplication.
