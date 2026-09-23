## Context

See proposal.md for motivation. This adds a third state transition to the amortization lifecycle already established for `Concepto`/`Deudor`: creation-time set → **[new] first-time activation** → correction (already shipped). It reuses every piece of existing machinery (`amortization_service.py`'s math, `entry_service.generar_entradas_amortizacion` / `cuota_deudor_service.generar_cuotas_amortizacion`, the existing `es_amortizada`/`es_amortizado`-branching balance calculations) — no new calculation logic is needed anywhere except the two new orchestration functions themselves.

## Goals / Non-Goals

**Goals:**
- Let a user add amortization terms to something that didn't have them, without deleting and recreating it.
- Never touch already-paid history.

**Non-Goals:**
- No automatic reconciliation of prior abonos/payments into the new schedule's starting point — the user manually supplies `valor_total`/`monto_total` and `cuota_inicial` to reflect reality, exactly as they already do at creation time for a loan that predates the app.
- No changes to the correction endpoints or their "must already be amortized" gate.

## Decisions

### Activation anchors at today, not at "after the last paid entry"
The correction path (`actualizar_amortizacion`) anchors its regenerated schedule at the month after the last paid installment, and derives `cuota_inicial` from `count(paid) + concepto.cuota_inicial` — this works there because the entity was ALREADY on a schedule, so "paid installments" are schedule installments with well-defined numbers. Here, the entity has never had a schedule: its existing paid entries (if any) are ad-hoc (`EntradaMensual.monto_planeado` set freely, no interest/principal split) or free-form (`Abono`), not tied to any installment number. There's no principled way to derive "which installment number are we on" from them. So activation behaves like fresh creation, mathematically: anchor = today, `cuota_inicial` = whatever the user explicitly provides (default 1) — identical to how creation already handles "I have a loan from before the app, I'm on installment N."

### Historical entries can collide with the new schedule's months — accepted, not solved
`generar_entradas_amortizacion` / `generar_cuotas_amortizacion` never overwrite an existing row for the same `(entity_id, anio, mes)` (this invariant already exists and is relied on elsewhere). If a pre-existing paid entry happens to occupy the same calendar month the new schedule would also want to use for one of its installments, that installment is silently skipped — the old entry wins, and the generated schedule will have fewer rows than `numero_cuotas` would suggest for that one month. This is accepted as a rare, self-resolving edge case (the user can already see it in the entry list) rather than solved with new reconciliation logic, consistent with the grilled decision to not attempt automatic reconciliation.

### New endpoints are POST, not PUT, on the same path as correction
`PUT /concepts/{id}/amortizacion` / `PUT /deudores/{id}/amortizacion` already mean "correct existing terms" and explicitly never accept `cuota_inicial`. Activation needs `cuota_inicial`. Rather than overload one schema with a field that means different things (or is sometimes forbidden) depending on state, `POST` on the same resource path cleanly means "create the amortization terms for the first time," mirroring ordinary REST semantics (POST creates, PUT replaces) without inventing a new URL shape.

## Risks / Trade-offs

- **A concept/debtor's principal (`valor_total`/`monto_total`) is re-stated at activation time, potentially replacing whatever value was there before.** Accepted — the user is expected to enter the real current figure at this point, per the grilled decision; this mirrors exactly what they'd have to do if deleting and recreating, just without losing history.
