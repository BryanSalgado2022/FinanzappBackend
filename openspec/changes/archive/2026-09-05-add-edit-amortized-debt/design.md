## Context

`generar_entradas_amortizacion(session, concepto, tabla, anio_inicio, mes_inicio, cuota_inicial=1)` (`app/services/entry_service.py:148-171`) already exists and does exactly what regeneration needs: given a full amortization table, it creates one entry per row from `cuota_inicial` onward, placing the first included row at `anio_inicio`/`mes_inicio` and advancing one calendar month per row, never overwriting an existing entry for the same `(concepto_id, anio, mes)`. It was written for creation-time generation but has no dependency on that context — it's reusable as-is for recalculation, provided the caller deletes conflicting unpaid entries first and passes the right `cuota_inicial`/anchor date. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Reuse `generar_entradas_amortizacion` unchanged rather than writing a second entry-generation code path.
- Never touch a paid entry's stored values, under any circumstance.

**Non-Goals:**
- Allowing `cuota_inicial` to change (explicitly out of scope, stays locked).
- Converting a non-amortized debt into an amortized one after creation (this change only covers *correcting* a debt that already has amortization data).

## Decisions

**Computing the next installment number to generate.** A concept's own generated entries occupy a contiguous run of installment numbers starting at `cuota_inicial` (default 1) — the entry-generation function guarantees this, since it's the only thing that has ever created entries for this concept. So: `n_pagadas = count(entries where pagado)`, and the next not-yet-generated installment number is `siguiente_numero = (concepto.cuota_inicial or 1) + n_pagadas`. This is exactly the `cuota_inicial` argument to pass into a fresh call to `generar_entradas_amortizacion` — it naturally skips every row already "used up" by a paid entry, whether or not those paid entries happen to be contiguous with unpaid ones in practice (an edge case the codebase doesn't otherwise guard against, e.g. marking a later month paid before an earlier one — not worth over-engineering for here).

**Validating `numero_cuotas` isn't reduced below what's paid.** Reject when `numero_cuotas < siguiente_numero - 1` (equivalently: `numero_cuotas < (cuota_inicial or 1) + n_pagadas - 1`) — there'd be no installments left in the new schedule for the entries that must stay.

**Anchor date for regeneration.** If any entry is paid, take the max `(anio, mes)` among paid entries and advance one month (small local month-math, same shape as `entry_service._sumar_meses` but not importing that "private" helper across modules — a two-line reimplementation in `concept_service.py` is simpler than promoting it to a public API for one caller). If nothing is paid, use today's `(year, month)`, matching creation-time behavior exactly.

**Deleting unpaid entries directly**, not via `entry_service.delete_entry` — that function explicitly rejects deletion on any fixed-window concept (amortized or `duracion_meses`), which is the right guard for the single-entry-delete endpoint but not applicable here, since this is a whole-concept recalculation deleting many rows at once as a controlled, intentional operation.

**Endpoint shape**: a dedicated `PUT /concepts/{id}/amortizacion` (or similar), not folded into the existing `PATCH /concepts/{id}`. The plain update endpoint's contract is "change one field, other fields untouched"; recalculation's contract is "replace all four terms together, entries get regenerated" — different enough semantics (and different validation: all four required together here, vs. all-optional on the plain PATCH) that conflating them would make both harder to reason about.

## Risks / Trade-offs

- [Risk] A recalculated schedule "doesn't perfectly line up" with what was already paid under the old terms (e.g. old cuota was 100.000, three were paid, new terms imply a different cuota for the remaining installments) — this is inherent to correcting terms mid-schedule, not a bug. → Mitigation: this was explicitly accepted by the user during grilling ("puede que el nuevo plan no encaje perfecto... es normal"); the frontend's confirmation step (sibling change) makes the scope of the change clear before committing to it.
- [Risk] Deleting and regenerating many entries in one request is a heavier operation than the existing single-field PATCH. → Mitigation: bounded by `numero_cuotas` (already a small, human-entered number, never large), no different in scale from creation-time generation.
