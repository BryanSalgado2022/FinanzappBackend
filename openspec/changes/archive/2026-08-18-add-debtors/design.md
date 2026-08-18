## Context

See proposal.md for motivation. Relevant current state:

- `Concepto` + `EntradaMensual` + `concept_service.py::saldo_restante` is the closest existing pattern: a parent entity with a total amount, a child entity recording payments, and a remaining balance computed at read time by summing the child rows and subtracting from the parent's total. `Deudor` + `Abono` follows the same shape, simplified (no monthly structure, no amortization).
- `app/routers/entries.py`'s `DELETE /{anio}/{mes}` (from the recently-archived `add-delete-monthly-entry` change) is the pattern for deleting a single child payment row nested under its parent, including how ownership is checked through the parent before touching the child.
- `Tarea` is the closest pattern for a simple, standalone, non-financial-concept entity with its own `activo`-equivalent boolean state (`completada` there, `activo` here — different semantics, same shape: a status flag independent of any computed value).
- No existing entity in this codebase has a required `date` field with no optional counterpart — `Tarea.fecha` is optional, `Concepto` doesn't have a plain date field at all (only `dia_vencimiento`, an int day-of-month). `Deudor.fecha` is the first *required* real date field.

## Goals / Non-Goals

**Goals:**
- Reuse the exact `saldo_restante` computation shape already established for debts, so this doesn't introduce a second way of computing "total minus payments" in the codebase.

**Non-Goals:**
- No summary/aggregate endpoint (`/deudores/summary`) — deliberately deferred per grilling; the list response already carries everything a future UI needs to compute its own aggregates.
- No abono update endpoint — only create and delete. A mis-entered abono is deleted and re-created, consistent with the reasoning already used for monthly entries (`add-delete-monthly-entry`'s proposal): edits to a payment record are rare enough that delete+recreate is simpler than building update semantics that would barely be used.
- No relation to `Concepto`, `Categoria`, or `Tarea` — fully standalone, per grilling.

## Decisions

**`Abono` as its own table with a direct `deudor_id` FK, not embedded JSON on `Deudor`.**
Matches `EntradaMensual`'s relationship to `Concepto` exactly: a real child table with `ondelete="CASCADE"` lets deleting a debtor cleanly remove its abonos at the database level (same mechanism already relied on for `monthly_entries` and `concepto_categoria`), rather than needing application-level cleanup code.

**`saldo_restante` computed via the same query shape as `concept_service.py::saldo_restante`.**
`select(func.coalesce(func.sum(Abono.monto), 0)).where(Abono.deudor_id == deudor.id)`, then `deudor.monto_total - Decimal(total_abonado)`. Unlike debts, there's no `cuota_inicial`-style "effective starting amount" wrinkle to account for — `monto_total` is always the correct starting point, since a `Deudor` has no amortization schedule or partial-history-outside-the-system concept. This makes the calculation strictly simpler than `Concepto`'s.

**Abono ownership validated through its parent `Deudor`, with no `user_id` on `Abono` itself.**
Exactly mirrors how `entries.py` validates a monthly entry's ownership by first loading and checking its parent `Concepto`'s `user_id`, rather than duplicating `user_id` onto the child row. Every abono endpoint (`POST`/`GET`/`DELETE`) first resolves the parent `Deudor` via `deudor_service.get_deudor(session, user_id, deudor_id)` (raising `DeudorNotFoundError` → 404 if it doesn't belong to the caller) before touching any `Abono` row.

**No `mes`/`anio` structure on `Abono` — a plain `fecha`, unlike `EntradaMensual`'s `anio`+`mes` pair.**
`EntradaMensual` is keyed by calendar month because it represents a *planned* monthly obligation with a uniqueness constraint (`uq_entry_concepto_anio_mes`) preventing two entries for the same month. An `Abono` is a point-in-time payment log entry with no such monthly cadence or uniqueness constraint — a debtor could receive two payments in the same week. A single `fecha: date` column is the correct, simpler shape here; do not copy the `anio`+`mes` pattern just because it's nearby.

## Risks / Trade-offs

[No summary endpoint means a future UI must fetch the full debtor list to compute aggregates, which won't scale if a user has hundreds of debtors] → Accepted: this mirrors the same trade-off already made for categories (no dedicated endpoint either), and realistic debtor counts for a personal finance app are small; revisit only if it becomes a measured problem.
