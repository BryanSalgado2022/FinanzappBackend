## Context

See proposal.md for motivation. Relevant current state:

- `Concepto` (`app/models/concepto.py`) already carries several optional, type-gated fields (`valor_total`, `tasa_interes`/`periodo_tasa`/`numero_cuotas`, `duracion_meses`), each validated in `ConceptoCreate` via `@model_validator(mode="after")` methods in `app/schemas/concepto.py`.
- `update_concepto` in `app/services/concept_service.py` is the single place that decides which fields are editable post-creation; it currently rejects `valor_total` changes when `es_amortizada(concepto)` is true.
- `app/routers/entries.py`'s `list_entries` and `upsert_entry` currently return the raw `EntradaMensual` ORM object directly, relying on FastAPI's `response_model=EntradaMensualRead` coercion. That coercion only works because every `EntradaMensualRead` field already exists as an attribute on `EntradaMensual` — `vencida` will not, since it depends on the parent `Concepto.dia_vencimiento`.

## Goals / Non-Goals

**Goals:**
- Add `dia_vencimiento` to `Concepto`, gated to `deuda`/`gasto_fijo`, mutable at any time.
- Compute `vencida` per monthly entry without the frontend re-implementing date logic.

**Non-Goals:**
- No new "immutable financial terms" bucket — `dia_vencimiento` is explicitly the first field on `Concepto` that is optional, type-gated, *and* always mutable. That's a one-line carve-out in `update_concepto`, not a new abstraction.
- No stored `vencida` column — it is derived, not persisted, to avoid a background job or trigger to keep it in sync as calendar dates pass.

## Decisions

### `vencida` is computed at read time in the router, not stored
`app/services/entry_service.py` gains a small pure function:

```python
def es_vencida(dia_vencimiento: int | None, anio: int, mes: int, pagado: bool) -> bool:
    if dia_vencimiento is None or pagado:
        return False
    return date(anio, mes, dia_vencimiento) < date.today()
```

Both endpoints in `app/routers/entries.py` already have the parent `Concepto` in hand (`list_entries` fetches it to authorize; `upsert_entry` fetches it to pass into `upsert_monthly_entry`), so both can call this function per entry and construct `EntradaMensualRead` explicitly instead of returning the raw ORM object. This mirrors the existing `_to_read` helper pattern in `app/routers/concepts.py`.

Alternative considered: store `vencida` as a column, refreshed by a scheduled job. Rejected — it's a pure function of three already-known values (day, year/month, paid status) and the current date; a stored/cached version would need invalidation logic for zero benefit at this data scale.

### `dia_vencimiento` validation lives alongside the existing per-type validators
Add a `validate_dia_vencimiento` method to `ConceptoCreate` next to `validate_valor_total`/`validate_duracion`, following the same shape: reject on `ingreso`, reject out-of-range (Pydantic's `Field(ge=1, le=28)` handles the range at the field level; the type-gating still needs the model validator, consistent with how `duracion_meses` does both). `ConceptoUpdate` gets a plain `dia_vencimiento: int | None = None` field; range checking happens in a small validator there too since `ConceptoUpdate` doesn't currently have any model-level validators — `update_concepto` does the `ingreso`-type check the same way it would need to know the concept's current type, which it already loads.

### Mutability carve-out is explicit, not a new field category
`update_concepto`'s existing `es_amortizada(concepto)` guard only blocks `valor_total`. Add `dia_vencimiento` as a plain, always-accepted parameter to `update_concepto` — no guard at all, including on amortized debts. The code comment on the field in `concepto.py` should say why (informational only, not part of any calculation), so a future reader doesn't assume it needs the same lock as its neighbors.

## Risks / Trade-offs

- **[Risk]** `es_vencida` uses `date.today()`, making the API response non-deterministic across calendar days (an entry flips from not-overdue to overdue with no write happening). → Acceptable and intentional: this mirrors how `saldo_restante` is already computed fresh on every read; nothing needs to poll for a background transition.
- **[Risk]** Duplicating the "construct read model manually" pattern in two router functions (`list_entries`, `upsert_entry`) instead of a shared helper. → Add one shared `_to_entry_read(concepto, entry)` helper in `app/routers/entries.py`, mirroring `_to_read` in `concepts.py`, so both call sites stay in sync.
