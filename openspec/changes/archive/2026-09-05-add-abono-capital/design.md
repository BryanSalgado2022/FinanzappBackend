## Context

See proposal.md for motivation. This reuses `Abono` (already exists, already has an `interes` field for the "how much was interest" distinction) rather than inventing a new ledger entity — a principal prepayment is just an `Abono` with `interes` always null (it's pure principal by definition).

## Goals / Non-Goals

**Goals:**
- Record a principal prepayment without losing the ability to see the debtor's *original* loan terms (`monto_total`, `numero_cuotas`) as historical record.
- Reuse the existing recalculation machinery (`amortization_service.py`, `cuota_deudor_service.generar_cuotas_amortizacion`) as much as possible.

**Non-Goals:**
- `Concepto` (the user's own debts) — confirmed out of scope with the user; it has no equivalent payment-ledger entity to extend.
- Reconstructing the pre-prepayment schedule if the recorded `Abono` is later deleted (see Risks).

## Decisions

### `monto_total`/`numero_cuotas` are never changed by a prepayment — `saldo_restante` and `cuota_fija` become derived differently instead
The obvious-looking approach — reduce `monto_total` by the prepayment amount, like `actualizar_amortizacion` already does for a full terms correction — was tried first and rejected: `monto_total` is displayed verbatim as "de $X prestados originalmente," and a prepayment silently shrinking that figure would corrupt the historical record of what was actually lent. So the debtor's stored terms (`monto_total`, `tasa_interes`, `periodo_tasa`, `numero_cuotas`, `cuota_inicial`) stay exactly as originally set (or last corrected via "Editar términos") — a prepayment never touches them except `numero_cuotas`, which is updated to reflect the new total installment count so the "Cuotas" summary figure stays accurate. Two consequences follow:

- **`saldo_restante`'s amortized branch also subtracts principal prepayments — gated on a new `Abono.es_abono_capital` flag, not every `Abono`.** The first version of this design summed every `Abono` for the debtor (mirroring the non-amortized branch's formula), but that broke `add-activate-amortization`'s explicit guarantee that abonos recorded *before* a debtor was amortized stay pure history and never feed the balance again (caught by that change's own test suite when implementing this one). An `Abono` row alone can't tell the two cases apart — nothing distinguished "recorded while non-amortized, now historical" from "recorded via a prepayment while already amortized." So `Abono` gains a new `es_abono_capital: bool` column (migration, default `false`), set `true` only by `registrar_abono_capital`; `saldo_restante`'s amortized branch sums `Abono.monto` filtered to `es_abono_capital=True` only. Regular `create_abono` stays blocked once amortized regardless, so this is always zero unless a prepayment was recorded.
- **`cuota_fija` becomes schedule-derived**, not recomputed from stored terms. Its old definition (`calcular_cuota_fija(monto_total, tasa, numero_cuotas)`) assumed those three fields alone describe one coherent fixed-payment table for the debt's entire life — true before this change, but no longer true once `numero_cuotas` can move independently of `monto_total` after a prepayment. The new definition reads the next not-yet-paid `CuotaDeudor`'s `monto_planeado` (falling back to the most recent entry if none are unpaid, or the stored-terms computation if no schedule exists at all yet). This is a strictly more robust definition — it always reflects the real schedule instead of a recomputation that could drift — and produces identical results to the old definition in every case that predates this change (creation, correction), since stored terms and the generated schedule were always consistent there.

### `reducir_plazo` needs new inverse math; `reducir_cuota` needs none
`reducir_cuota` (same remaining installment count, lower installment) is exactly what `actualizar_amortizacion` already computes — given a principal and installment count, `calcular_cuota_fija` derives the fixed payment. `reducir_plazo` needs the inverse: given a principal and a *fixed* installment (the current one, unchanged), how many installments pay it off. `amortization_service.calcular_cuotas_restantes` answers this by simulating the same per-period interest/capital split `generar_tabla_amortizacion` already uses, incrementing a counter until the balance reaches zero, rather than a closed-form log formula — kept in `Decimal` throughout (no new float usage), consistent with the rest of that module, and it naturally raises when the fixed installment doesn't even cover one period's interest (an infinite loop otherwise).

Once the installment count is known (either way), the remaining schedule is generated exactly like `actualizar_amortizacion` already does: a fresh `generar_tabla_amortizacion(nuevo_saldo, tasa_mensual, numero_cuotas_restantes)` for a *mini* table representing just the unpaid remainder, generated with `cuota_inicial=1` (it's self-contained — the real installment numbering, "which cuota this actually is in the debtor's lifetime," is tracked implicitly the same way it always is: `cuota_inicial + count(paid)`). Because `reducir_plazo` picks the installment count as the smallest that keeps the payment at or below the original, the freshly recomputed cuota_fija for that count will match the original almost exactly, differing by at most a cent or two of rounding — consistent with how real lenders' "keep paying the same" prepayment options behave.

### The debtor's `Abono` history is authoritative; the generated schedule is not retroactively reconciled if it's deleted
Deleting a principal-prepayment `Abono` restores the balance calculation immediately (since `saldo_restante` sums `Abono` rows live), but does **not** regenerate the longer pre-prepayment schedule — that regeneration already happened and isn't reversible from history alone. Accepted as a known limitation, consistent with this codebase's existing stance on not attempting automatic reconciliation (see `add-activate-amortization`'s design.md for the same call). A user who deletes a prepayment by mistake and wants the old schedule back needs to use "Editar términos" to re-specify it.

## Risks / Trade-offs

- **`cuota_fija`'s signature changes** (now takes `session`) — a real, if small, change to already-shipped, tested code. Mitigated: every existing call site is updated, and the new definition is provably identical to the old one in every pre-existing scenario (creation, correction), so no existing test should change behavior.
- **Deleting a capital-prepayment `Abono` doesn't restore the old schedule** (see above) — accepted trade-off, not solved here.
