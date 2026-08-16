## Context

Builds on the `add-budget-mvp` change (now archived; see `openspec/specs/budget-concepts/` and `openspec/specs/monthly-budget/` for the baseline). Debts today have `valor_total` and a remaining balance computed from actual payments — no interest, no installment count, no schedule. This design adds an optional, additive layer for users who want real amortization math, without touching how non-amortized debts or other concept types behave.

## Goals / Non-Goals

**Goals:**
- Fixed-installment (French method) amortization: given principal, rate, and installment count, compute the fixed monthly payment and the full interest/principal breakdown per installment.
- Let the user enter the rate as either monthly or annual, converting internally.
- Aggregate debt view and an annual planned-vs-actual trend, per the user's request after using the MVP.

**Non-Goals:**
- Editing an existing amortization schedule (interest rate or installment count) — the user explicitly asked for delete-and-recreate instead, to avoid recalculation complexity.
- Any data import/migration tooling — out of scope per the user (replacing the spreadsheet going forward, not migrating its history).
- Envelope-style budget categories (Necesidades/Deseos/Deudas/Futuro) — deferred.
- Frontend changes — this change is backend-only; the "Deudas" screen and trend chart land in a separate frontend change once this API exists.

## Decisions

### Amortization fields live on `Concepto`, not a separate table
Add `tasa_interes` (nullable numeric), `periodo_tasa` (nullable enum: `mensual` | `anual`), and `numero_cuotas` (nullable int) directly to the `concepts` table. The computed schedule itself (per-installment interest/principal/balance) is **not stored** — it's derived on demand from `valor_total`, `tasa_interes`, `periodo_tasa`, and `numero_cuotas`, which are already immutable once set. Auto-generation writes the schedule's installment *amount* into `monto_planeado` on the normal `monthly_entries` rows (no new table), exactly as today's auto-generation does for other concepts.

**Rationale**: since the inputs are frozen after creation, the schedule is a pure function of those four fields — storing it separately would be a second source of truth for data that never changes. Computing it on the fly (a closed-form loop, O(numero_cuotas)) is cheap enough at this scale (at most a few hundred installments).

**Alternative considered**: a dedicated `debt_schedule` table with one row per installment. Rejected — adds a migration and a sync concern for zero benefit, since the four source fields are immutable and the calculation is trivial to redo.

### Fixed-installment formula and rate conversion
Standard French/cuota-fija formula: `cuota = P * i / (1 - (1 + i)^-n)`, where `P` = `valor_total`, `i` = monthly rate, `n` = `numero_cuotas`. When `periodo_tasa = anual`, convert with the effective-rate formula `i_mensual = (1 + i_anual)^(1/12) - 1` (matches how Colombian banks quote E.A. rates) rather than a naive `/12` division.

**Rationale**: `/12` is the flat/nominal approximation and would silently produce a payment that doesn't match what the bank actually charges; the effective-rate conversion matches real bank statements, which is the whole point of this feature (the user's stated pain point was a calculated amount not matching reality).

### Immutability enforced at the schema layer
`ConceptoUpdateInput` (the PATCH request schema) drops `valor_total` as an accepted field whenever the target concept already has `tasa_interes`/`numero_cuotas` set; the service layer re-validates this server-side regardless of what the client sends (never trust client omission alone). `tasa_interes`, `periodo_tasa`, and `numero_cuotas` are never accepted on update at all — they can only be set at creation.

**Rationale**: matches the user's explicit "delete and recreate instead of editing" decision, and removing the field from the update path structurally prevents the recalculation complexity they wanted to avoid, rather than relying on a runtime check that could be bypassed by a future code change.

### Auto-generation: full schedule at creation, not year-by-year
Unlike `gasto_fijo`/non-amortized `deuda` (which only auto-generate through December of the current year and extend later via edits), an amortized debt generates monthly entries for *all* `numero_cuotas` installments at creation time, even into future years. Each entry's `monto_planeado` is the fixed installment amount from the schedule for that position.

**Rationale**: the whole schedule is known upfront (that's the point of amortization), so there's no reason to defer generating months 13+ the way we defer for open-ended recurring concepts whose future amount isn't yet known.

**Risk**: a very long schedule (e.g., a 360-month mortgage) generates 360 rows at once. Acceptable at this scale (single-user, a handful of debts); revisit if it ever becomes a performance concern.

### `debts-summary` as its own capability, not folded into `budget-concepts`
`GET /debts/summary` and `GET /summary/annual` are new endpoints under a new `debts-summary` capability rather than extending the existing `GET /summary` (monthly) endpoint, because they answer a different question (aggregate across all debts / across a year) than the existing one (single month, all concept types).

## Risks / Trade-offs

- [Floating-point rounding across many installments could leave a few cents of drift by the final installment] → Mitigated by rounding each installment amount to 2 decimals and adjusting the final installment to force the schedule's ending balance to exactly zero, consistent with how the existing `saldo_restante` calculation already floors at zero.
- [A 360-month schedule generated at once is a lot of rows for one request] → Acceptable at current scale; revisit batching/pagination only if it becomes a real bottleneck.
- [Users may expect to "fix a typo" in the rate/installment count and be surprised they can't] → Mitigated by making the immutability behavior explicit in the API error message and documenting it in the frontend copy when that change lands.

## Open Questions

- Exact response shape/field names for `GET /debts/summary` and `GET /summary/annual` — implementation detail, doesn't change the spec's externally observable behavior; decide during implementation.
