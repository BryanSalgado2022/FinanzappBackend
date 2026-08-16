## Context

Builds on the archived `add-budget-mvp` and `add-debt-amortization` changes. `entry_service.py` already has two generation patterns to draw from: `_fill_forward` (open-ended, through December, skip-existing) and `generar_entradas_amortizacion` (a known-length schedule generated fully at creation, skip-existing). Fixed-duration recurring concepts are structurally the amortization case with a flat amount instead of a computed schedule — reuse that shape rather than inventing a third pattern.

## Goals / Non-Goals

**Goals:**
- `ingreso` gets the same auto-generation `gasto_fijo` already has.
- An optional, immutable `duracion_meses` on `gasto_fijo`/`ingreso` that generates its whole known window at creation, mirroring how amortized debts already do this.

**Non-Goals:**
- Duration for `deuda` — it already has `numero_cuotas` (via amortization) or is open-ended; adding a second, different duration concept to debts would be confusing, not additive.
- Editing `duracion_meses` after creation — immutable, same rationale as the amortization fields (avoid a recalculation flow).
- Frontend changes — separate change.

## Decisions

### `duracion_meses` reuses the amortization-schedule generation shape, not `_fill_forward`
Add a new `entry_service.generar_entradas_recurrentes(session, concepto, monto_planeado, anio_inicio, mes_inicio, duracion_meses)` that mirrors `generar_entradas_amortizacion`'s loop (fixed count, spans years, skip-existing) but writes the same flat `monto_planeado` for every month instead of a computed schedule. Called once at creation, same as the amortization path.

**Rationale**: `_fill_forward`'s "through December, extend via edits" shape exists specifically because an open-ended concept's future length is unknown. A `duracion_meses` concept's length *is* known at creation - reusing the amortization shape means no special-casing is needed later, since skip-existing already guarantees editing a month within the window never generates entries beyond it.

### `RECURRING_TYPES` gains `ingreso`
`entry_service.RECURRING_TYPES = (TipoConcepto.DEUDA, TipoConcepto.GASTO_FIJO)` becomes `(..., TipoConcepto.INGRESO)`. This one-line change is what makes `_fill_forward`/`upsert_monthly_entry`'s existing open-ended path apply to income too, for the case with no `duracion_meses`.

### Router branching order in `create_concept`
Three mutually exclusive generation paths, checked in order: (1) debt with amortization data → existing schedule generation, (2) `gasto_fijo`/`ingreso` with `duracion_meses` set → new fixed-window generation, (3) otherwise, existing open-ended `upsert_monthly_entry` path if `monto_planeado` was given. `duracion_meses` and amortization data are mutually exclusive by construction (validation rejects `duracion_meses` on `deuda`, and amortization only applies to `deuda`), so no path can be ambiguous.

## Risks / Trade-offs

- [A very large `duracion_meses` generates that many rows at once] → Same accepted trade-off as amortization schedules (design.md of `add-debt-amortization`); fine at this scale.
- [User sets a short `duracion_meses` and later wants it to continue] → By design, immutable — the guidance (same as amortization terms) is to mark it finished and create a new concept for the continuation. Not revisited here since the user didn't ask for editable duration.

## Open Questions

None - scope was fully resolved via direct clarification before this design was written.
