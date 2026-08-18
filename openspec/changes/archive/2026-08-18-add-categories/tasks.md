## 1. Categoria model and schema

- [x] 1.1 Create `app/models/categoria.py`: `Categoria` (table `categorias`) with `id`, `user_id` (FK `users.id`, indexed), `nombre`, `emoji: str | None`, `created_at`; module-level `ALLOWED_CATEGORIA_EMOJIS` constant with the curated set from design.md
- [x] 1.2 Create the `concepto_categoria` link table (composite PK `concepto_id`+`categoria_id`, both FKs with `ondelete="CASCADE"`)
- [x] 1.3 Register `Categoria` in `app/models/__init__.py`
- [x] 1.4 Create `app/schemas/categoria.py`: `CategoriaCreate` (`nombre`, optional `emoji`), `CategoriaUpdate` (optional `nombre`, optional `emoji`), `CategoriaRead` (`id`, `nombre`, `emoji`), with a validator rejecting any `emoji` not in `ALLOWED_CATEGORIA_EMOJIS`

## 2. Categoria service and router

- [x] 2.1 Create `app/services/categoria_service.py`: `CategoriaNotFoundError`, `create_categoria` (case-insensitive find-or-create by `nombre` scoped to `user_id`), `list_categorias`, `get_categoria`, `update_categoria`, `delete_categoria`
- [x] 2.2 Create `app/routers/categorias.py`: `POST /categorias`, `GET /categorias`, `GET /categorias/{id}`, `PATCH /categorias/{id}`, `DELETE /categorias/{id}` — same auth/ownership/404 pattern as `app/routers/concepts.py`
- [x] 2.3 Register the new router in `app/main.py`

## 3. Wire categories into concepts

- [x] 3.1 Remove `categoria: str | None` from `app/models/concepto.py`; add the relationship to `Categoria` via the link table
- [x] 3.2 Update `app/schemas/concepto.py`: replace `categoria` with `categoria_ids: list[int] | None` on `ConceptoCreate`/`ConceptoUpdate`; replace `categoria` with `categorias: list[CategoriaRead]` on `ConceptoRead`
- [x] 3.3 Update `app/services/concept_service.py`: `create_concepto`/`update_concepto` accept `categoria_ids`, validate each id exists and belongs to `user_id` (raise a descriptive `ValueError` otherwise), and set the concept's category assignments accordingly (create replaces nothing since it's new; update replaces the full set only when `categoria_ids` is not `None`, per design.md's None-vs-[] rule)
- [x] 3.4 Update `app/routers/concepts.py`: thread `categoria_ids` through create/update, update `_to_read` to build `categorias` from the concept's assigned `Categoria` rows

## 4. Migration

- [x] 4.1 Generate the Alembic revision (schema: create `categorias` and `concepto_categoria`, drop `concepts.categoria`)
- [x] 4.2 Add the data-migration step inside the same revision's `upgrade()`: for each distinct non-null `(user_id, categoria)` pair in `concepts`, insert a `categorias` row and link every matching concept, via raw SQL through `op.get_bind()`, before dropping the column
- [x] 4.3 Write a best-effort `downgrade()` that re-adds `concepts.categoria` and backfills it from one linked category per concept (documented as lossy per design.md)

## 5. Tests

- [x] 5.1 `tests/test_categorias.py`: create (including find-or-create-by-name idempotency, case-insensitive), list scoped to owner, get scoped to owner (404 for another user's category), update propagates to concepts using it, delete unassigns from concepts without error, emoji validation (accepted set vs. rejected value)
- [x] 5.2 Update `tests/test_concepts.py`: creating/updating a concept with `categoria_ids` (valid ids, empty list, omitted field, invalid/foreign id rejected with 422), concept read response includes full category objects
- [x] 5.3 Run the full suite (`docker compose exec -T api python -m pytest -q`) and confirm no regressions

## 6. Docs

- [x] 6.1 Update `README.md`'s endpoint table with the 5 new `/categorias` endpoints and the changed `categoria_ids`/`categorias` shape on concept endpoints
- [x] 6.2 Add a bullet to "Decisiones clave a recordar" covering: categories are global per user, many-to-many, optional, find-or-create-by-name on `POST /categorias`, deleting a category silently unassigns it, `None` vs `[]` semantics on `categoria_ids` in updates, and the fixed emoji set

## 7. Manual verification

- [x] 7.1 Via curl against a throwaway instance pointed at a copy of the real data: create categories (including a duplicate name to confirm find-or-create), assign multiple to a concept, rename one and confirm the concept's response reflects it, delete one in use and confirm the concept keeps its other categories, attempt an invalid emoji and confirm 422
- [x] 7.2 Confirm the migration runs cleanly against a copy of the real data and produces correctly-linked `categorias` rows (11 rows in practice, not 9, since categories are scoped per user and 2 of the 9 name strings were shared across the account's 2 users, each becoming a separate per-user row)
