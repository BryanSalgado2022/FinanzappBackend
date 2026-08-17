## Context

See proposal.md for motivation. Relevant current state:

- `app/services/amortization_service.py::generar_tabla_amortizacion(principal, tasa_mensual, numero_cuotas)` returns a list of dicts, one per installment (1-indexed via `numero`), each with `cuota`, `interes`, `abono_capital`, and `saldo` (the balance remaining *after* that installment is paid).
- `app/services/entry_service.py::generar_entradas_amortizacion(session, concepto, tabla, anio_inicio, mes_inicio)` iterates the full table and creates one entry per row, offsetting from `anio_inicio/mes_inicio` by `fila["numero"] - 1` months.
- `app/services/concept_service.py::saldo_restante(session, concepto)` is `concepto.valor_total - sum(monto_pagado across all entries)`, floored at zero. `es_amortizada(concepto)` checks `tasa_interes is not None and numero_cuotas is not None`.
- `app/services/entry_service.py::_fill_forward(session, concepto, monto_planeado, anio, desde_mes)` fills `desde_mes..12` of `anio`, skipping existing entries, and is the exact primitive needed for the year-extension feature - no new fill logic needed, just a new caller.
- `app/routers/entries.py::list_entries` already loads the parent `concepto` before calling `entry_service.list_entries` - the natural insertion point for lazy generation, before the entries are fetched.
- `entry_service.upsert_monthly_entry` already has an inline `tiene_ventana_fija = concepto.duracion_meses is not None or (concepto.tasa_interes is not None and concepto.numero_cuotas is not None)` check; the year-extension logic reuses this exact inline form rather than importing `concept_service.es_amortizada`, avoiding a new cross-module dependency for a one-line check.

## Goals / Non-Goals

**Goals:**
- Both features reuse existing generation primitives (`generar_tabla_amortizacion`'s row shape, `_fill_forward`) rather than introducing parallel logic.
- Zero new infrastructure (no scheduler, no background worker).

**Non-Goals:**
- No backfilling of multi-year gaps beyond the current year in one pass (see Risks) - a concept unopened for 2+ years only catches up to the current year when finally viewed, not every skipped year.
- No UI for entering historical (pre-`cuota_inicial`) payments - those installments simply have no entries, by design (they were paid outside the app).

## Decisions

### `cuota_inicial` shifts which schedule rows get entries and where they land
`generar_entradas_amortizacion` gains a `cuota_inicial: int = 1` parameter:
```python
def generar_entradas_amortizacion(session, concepto, tabla, anio_inicio, mes_inicio, cuota_inicial=1):
    for fila in tabla:
        if fila["numero"] < cuota_inicial:
            continue
        anio, mes = _sumar_meses(anio_inicio, mes_inicio, fila["numero"] - cuota_inicial)
        ...
```
The offset changes from `fila["numero"] - 1` to `fila["numero"] - cuota_inicial` so the first *generated* installment always lands in the creation month, regardless of its number in the schedule - the user's actual calendar shouldn't shift just because they're joining partway through.

### Effective starting amount for `saldo_restante`
Add `valor_total_efectivo(concepto) -> Decimal | None` to `concept_service.py`:
```python
def valor_total_efectivo(concepto: Concepto) -> Decimal | None:
    if concepto.valor_total is None:
        return None
    if not concepto.cuota_inicial or concepto.cuota_inicial <= 1 or not es_amortizada(concepto):
        return concepto.valor_total
    tasa_mensual = tasa_mensual_desde(concepto.tasa_interes, concepto.periodo_tasa)
    tabla = generar_tabla_amortizacion(concepto.valor_total, tasa_mensual, concepto.numero_cuotas)
    return tabla[concepto.cuota_inicial - 2]["saldo"]  # balance after the installment just before cuota_inicial
```
`saldo_restante` calls this instead of reading `concepto.valor_total` directly. This recomputes the schedule on every call, same as `cuota_fija` already does today - no caching, consistent with the project's "compute fresh on read" convention (see README). Cheap in practice (schedules are at most a few hundred rows).

Alternative considered: store the effective starting balance as its own column at creation time. Rejected - it would duplicate data already derivable from existing fields, and diverge from the "compute fresh" pattern used everywhere else in this codebase (`saldo_restante`, `cuota_fija`).

### `cuota_inicial` validation and immutability
`ConceptoCreate` gains `cuota_inicial: int | None = Field(default=None, ge=1)`, with a new `@model_validator(mode="after")`:
- Reject if set and not `es_amortizada`-equivalent (i.e. `tasa_interes`/`numero_cuotas` not both present) - mirrors the existing `validate_amortizacion`/`validate_dia_vencimiento` pattern.
- Reject if `cuota_inicial > numero_cuotas` (only checkable once both fields are known to be present).

`ConceptoUpdate` gains `cuota_inicial: int | None = None` *purely so it can be explicitly rejected* - `update_concepto` raises `ValueError("cuota_inicial cannot be changed after creation; delete this concept and create a new one instead")` whenever it's provided, unconditionally (no exceptions, unlike `valor_total` which is only locked once amortized - `cuota_inicial` only ever exists on an amortized debt in the first place, so there's no "unlocked" case for it). This surfaces as a 422 with that message via the router's existing `except ValueError as exc: raise HTTPException(422, detail=str(exc))` - already wired, no router change needed beyond passing the field through.

### Lazy year-extension hooks into `list_entries`, not a new endpoint
`entry_service` gains:
```python
def asegurar_entradas_anio_actual(session: Session, concepto: Concepto) -> None:
    if concepto.tipo not in RECURRING_TYPES or not concepto.activo:
        return
    tiene_ventana_fija = concepto.duracion_meses is not None or (
        concepto.tasa_interes is not None and concepto.numero_cuotas is not None
    )
    if tiene_ventana_fija:
        return
    today = date.today()
    if get_entry(session, concepto.id, today.year, today.month) is not None:
        return
    ultima_entrada = session.exec(
        select(EntradaMensual)
        .where(EntradaMensual.concepto_id == concepto.id)
        .order_by(EntradaMensual.anio.desc(), EntradaMensual.mes.desc())
    ).first()
    if ultima_entrada is None:
        return
    if (ultima_entrada.anio, ultima_entrada.mes) > (today.year, today.month):
        return  # latest entry is in the future - nothing to catch up from
    _fill_forward(session, concepto, ultima_entrada.monto_planeado, today.year, today.month)
```
The future-entry guard was added during implementation: `ConceptoCreate`'s optional `anio`/`mes` override (added to fix concept creation always seeding the real server month instead of whatever month the Dashboard was viewing) means a concept's *only* entry can already be months ahead of the real current month. Without the guard, the lazy-fill would misfire and backfill the months between real-today and that future entry using the future entry's amount - a different, undesired case this feature was never meant to cover.
`app/routers/entries.py::list_entries` calls this once, right after loading `concepto` and before `entry_service.list_entries(...)`. This is a read endpoint performing a write as a side effect - acceptable here because it's idempotent (safe to call every time; does nothing once the gap is filled) and mirrors the project's existing precedent of generation-on-mutation (`upsert_monthly_entry` already does the analogous thing on write). No new endpoint, no client-visible behavior change beyond "the entries that should exist, now do."

**Multi-year gap**: if a concept hasn't been viewed in 2+ years, only the *current* year gets filled the first time it's viewed again - the skipped year(s) in between stay permanently ungenerated. This matches exactly what was specified in grilling (fill through December of the *current* year using the most recent known amount) and avoids guessing amounts for years with zero visibility. Documented as a known, accepted limitation rather than solved with speculative multi-year backfill logic.

## Risks / Trade-offs

- **[Risk]** `valor_total_efectivo` recomputes the full amortization table on every `saldo_restante` call for debts with `cuota_inicial` set. → Same cost profile as the already-shipped `cuota_fija`, which does the same recomputation; not a new performance concern at this data scale.
- **[Risk]** Lazy generation on a GET has a side effect (a DB write) that isn't obvious from the endpoint's shape. → Documented here and in code comments; consistent with the project's existing "generate the known window" philosophy, just moved to trigger on read instead of exclusively on write for this one case.
- **[Trade-off]** Multi-year gaps beyond the current year are never backfilled automatically (see Non-Goals). → Acceptable: the grilled requirement was specifically "extend into the current year," not "reconstruct arbitrary history."
