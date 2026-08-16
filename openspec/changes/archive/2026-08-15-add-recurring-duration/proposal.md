## Why

Recurring income (like a salary) currently gets no auto-generation at all — only `deuda`/`gasto_fijo` concepts do. As the user put it, that means re-entering the same salary amount every single month by hand, which is exactly the repetitive task this app is meant to eliminate. Fixing this raises a second question: for how long should a recurring concept keep generating? Today's only answer is "indefinitely, until you finish or delete it" — fine for an ongoing salary or rent, but not for a concept the user knows in advance has a fixed lifespan (e.g. a 6-month contract income, or a subscription ending in 3 months).

## What Changes

- `ingreso` concepts are now included in monthly auto-generation, exactly like `gasto_fijo` today (previously only `deuda`/`gasto_fijo` auto-generated).
- Add an optional `duracion_meses` field to `gasto_fijo` and `ingreso` concepts (rejected on `deuda`, which already has its own duration concept via amortization's `numero_cuotas`, or is open-ended otherwise). When set together with an initial planned amount at creation, the system generates monthly entries for exactly that many consecutive months (spanning into future years if needed) and then stops — no further auto-generation, matching the user's explicit request to control "for how long" a recurring amount repeats.
- When `duracion_meses` is not set, `gasto_fijo`/`ingreso` behave exactly as before this change (indefinite, auto-generates through December of the current year, extends forward as the user edits the current month).

**BREAKING**: None. `ingreso` previously never got monthly entries auto-generated from `monto_planeado` at creation — that was silently ignored. This change makes it apply, which is additive (no prior behavior relied on it being ignored).

## Capabilities

### Modified Capabilities
- `budget-concepts`: `gasto_fijo`/`ingreso` concepts can optionally declare `duracion_meses`.
- `monthly-budget`: auto-generation now includes `ingreso`; a fixed-duration recurring concept generates its whole known window at creation instead of the open-ended through-December behavior.

## Impact

- `FinanzappBackend`: new nullable column on `concepts`, changed auto-generation logic, validation on concept creation.
- `FinanzappFrontend`: out of scope for this change — a separate change adds the duration field to the concept form and splits the Dashboard's concept list into three grouped tables (deuda/gasto_fijo/ingreso), which the user also requested.

## Out of Scope (backlog, not part of this change)

- Duration for `deuda` concepts without amortization data (their "end" is implicitly reaching a zero balance, not a fixed month count).
- Editing `duracion_meses` after creation (immutable, same rationale as the amortization fields: no recalculation flow).
