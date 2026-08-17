## Context

See proposal.md for motivation. `app/services/entry_service.py` already has the exact "fixed window" check inlined twice (`upsert_monthly_entry`, `asegurar_entradas_anio_actual`):
```python
tiene_ventana_fija = concepto.duracion_meses is not None or (
    concepto.tasa_interes is not None and concepto.numero_cuotas is not None
)
```
This change reuses that same inline pattern rather than extracting a shared helper - consistent with how the existing two call sites already duplicate it instead of factoring it out.

## Goals / Non-Goals

**Goals:** Minimal, single-purpose deletion path reusing existing lookup/validation helpers (`concept_service.get_concepto`, `entry_service.get_entry`).

**Non-Goals:** No change to the year-extension behavior from the prior change - a deleted current-month entry may still come back on next visit, by design (see proposal.md).

## Decisions

### Reject fixed-window deletion with 409 Conflict, not 422
The rest of the entries API uses 422 for request-shape validation (e.g. `mes` out of 1-12) and 404 for missing resources. Rejecting a delete because of the concept's *state* (it has a schedule) rather than the *request's* shape is a conflict with the current state of the resource, not an unprocessable request body - 409 is the more accurate HTTP semantic and doesn't collide with the existing 422 meaning ("your request shape is invalid") used elsewhere in this router. `ConceptoNotFoundError`/entry-not-found both still map to 404, unchanged.

### `entry_service.delete_entry(session, concepto, anio, mes)` raises a dedicated exception
```python
class EntradaConVentanaFijaError(Exception):
    pass

def delete_entry(session: Session, concepto: Concepto, anio: int, mes: int) -> None:
    tiene_ventana_fija = concepto.duracion_meses is not None or (
        concepto.tasa_interes is not None and concepto.numero_cuotas is not None
    )
    if tiene_ventana_fija:
        raise EntradaConVentanaFijaError()
    entry = get_entry(session, concepto.id, anio, mes)
    if entry is None:
        raise EntryNotFoundError()
    session.delete(entry)
    session.commit()
```
The router maps `EntradaConVentanaFijaError` → 409 and the not-found case → 404, mirroring the existing `ConceptoNotFoundError` → 404 mapping already used throughout `app/routers/concepts.py`/`entries.py`.

## Risks / Trade-offs

- **[Trade-off]** No new `EntryNotFoundError` exists yet in the codebase (existing code just returns `None` from `get_entry` and callers handle it inline). Adding one here is a small new pattern, scoped to this one delete path - acceptable since `upsert_monthly_entry`'s `None`-then-create behavior doesn't need the same "entry must already exist" signal that delete does.
