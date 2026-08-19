## Context

See proposal.md - Why. Three independent additions, bundled into one change because they're all prep work for the same downstream feature (the Agenda calendar) and none depends on the others.

## Goals / Non-Goals

**Goals:**
- Each new date is set automatically by the backend from a state transition (paid/unpaid, active/inactive) - never accepted as free-form input from the client.

**Non-Goals:**
- Letting a user specify an arbitrary past date for `fecha_pago` or `finalizado_en` (e.g. "I actually paid this three days ago") - not requested; these always reflect "today," matching how `Concepto.created_at`/`Deudor.created_at` already work (server-assigned, not client-supplied).
- Backfilling `fecha_pago`/`finalizado_en` for entries/concepts/debtors already paid/finished before this change ships - they simply have `null` for these new fields until their next state change, which is acceptable since the Agenda only needs this going forward.

## Decisions

**`dia_vencimiento` for `ingreso`: delete the type check, nothing else changes.** `ConceptoCreate.validate_dia_vencimiento` and `concept_service.update_concepto`'s inline `if concepto.tipo == TipoConcepto.INGRESO: raise ValueError(...)` guard are both removed outright. No new validator needed - the field's existing range check (`ge=1, le=28`) already applies uniformly.

**`fecha_pago` set inside `entry_service._save_entry`, the single choke point every entry write already goes through** (both the manual upsert endpoint and the internal fill-forward/amortization generators construct `EntradaMensual` directly rather than through `_save_entry`, so this only affects entries a user actually marks paid/unpaid through the API - generated-but-unpaid entries correctly get no `fecha_pago`). Logic: `if pagado and not entry.pagado: entry.fecha_pago = date.today()` (transitioning to paid) / `elif not pagado: entry.fecha_pago = None` (unpaid, whether it was paid before or not) - checked against the entry's *prior* `pagado` value before it's overwritten, so re-saving an already-paid entry (e.g. editing `monto_pagado` without touching `pagado`) leaves `fecha_pago` untouched rather than bumping it to today again.

**`finalizado_en` set inside `concept_service.update_concepto` / `deudor_service.update_deudor`, right alongside the existing `activo` assignment**, using the same before/after comparison shape as `fecha_pago`: `if activo is not None and activo != concepto.activo: concepto.finalizado_en = date.today() if not activo else None`. Symmetric handling of both directions (closing sets it, reactivating clears it) rather than only handling the close path, since the update functions already accept `activo: true` as a valid transition today (nothing currently prevents reactivating) and leaving a stale `finalizado_en` on a reactivated concept/debtor would be a latent bug the first time the Agenda reads it.

**One combined Alembic migration**, not three - all three columns are simple nullable `date` additions to three different tables with no data migration needed, so splitting them into separate migrations would add ceremony without any benefit (they're not independently reversible in any meaningful way - reverting the Agenda backend prep means reverting all three together).

## Risks / Trade-offs

- [`fecha_pago`/`finalizado_en` always reflect "today" server-side, never a user-chosen past date] → Accepted per Non-Goals; if the user later wants to backfill or correct these (e.g. "I actually finished paying last Tuesday, not today"), that's a distinct, explicit feature request, not assumed here.
