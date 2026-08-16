## 1. Data model and migration

- [x] 1.1 Add nullable `dia_vencimiento: int | None` to `Concepto` in `app/models/concepto.py`, with a comment noting it's informational-only and always mutable (not subject to the amortization immutability rule)
- [x] 1.2 Generate and write an Alembic migration adding the `dia_vencimiento` column to `concepts`, following the pattern of the `duracion_meses` migration

## 2. Schemas and validation

- [x] 2.1 Add `dia_vencimiento: int | None = Field(default=None, ge=1, le=28)` to `ConceptoCreate` in `app/schemas/concepto.py`
- [x] 2.2 Add a `validate_dia_vencimiento` model validator to `ConceptoCreate` rejecting `dia_vencimiento` when `tipo == TipoConcepto.INGRESO`
- [x] 2.3 Add `dia_vencimiento: int | None = Field(default=None, ge=1, le=28)` to `ConceptoUpdate`
- [x] 2.4 Add `dia_vencimiento: int | None` to `ConceptoRead`
- [x] 2.5 Add `vencida: bool` to `EntradaMensualRead` in `app/schemas/entrada_mensual.py`

## 3. Service layer

- [x] 3.1 Add `dia_vencimiento` parameter to `create_concepto` in `app/services/concept_service.py` and pass it through to the `Concepto` constructor
- [x] 3.2 Add `dia_vencimiento` parameter to `update_concepto`, always applied (no immutability guard), and reject it there if the concept's `tipo` is `ingreso`
- [x] 3.3 Add `es_vencida(dia_vencimiento, anio, mes, pagado) -> bool` to `app/services/entry_service.py` per design.md

## 4. Routers

- [x] 4.1 Pass `payload.dia_vencimiento` through in `create_concept` (`app/routers/concepts.py`) and add `dia_vencimiento=concepto.dia_vencimiento` to `_to_read`
- [x] 4.2 Pass `payload.dia_vencimiento` through in `update_concept`
- [x] 4.3 Add a `_to_entry_read(concepto, entry)` helper in `app/routers/entries.py` that builds `EntradaMensualRead` explicitly, computing `vencida` via `entry_service.es_vencida`
- [x] 4.4 Update `list_entries` and `upsert_entry` in `app/routers/entries.py` to return `_to_entry_read(...)` instead of the raw ORM object/list

## 5. Tests

- [x] 5.1 Test creating a `deuda`/`gasto_fijo` concept with a valid `dia_vencimiento` saves it
- [x] 5.2 Test rejecting `dia_vencimiento` outside 1-28
- [x] 5.3 Test rejecting `dia_vencimiento` on an `ingreso` concept
- [x] 5.4 Test updating `dia_vencimiento` via PATCH, including on an amortized debt (must succeed, unlike `valor_total`)
- [x] 5.5 Test `vencida` is true for an unpaid entry whose computed due date has passed
- [x] 5.6 Test `vencida` is false for a paid entry regardless of due date
- [x] 5.7 Test `vencida` is false when the concept has no `dia_vencimiento` set
- [x] 5.8 Run the full test suite inside the `api` container and confirm all tests pass

## 6. Manual verification

- [x] 6.1 Restart the `api` container so the code changes take effect (no `--reload`)
- [x] 6.2 Verify via API (curl or the existing frontend) that `GET /concepts/{id}` returns `dia_vencimiento` and `GET /concepts/{id}/entries` returns `vencida` per entry
