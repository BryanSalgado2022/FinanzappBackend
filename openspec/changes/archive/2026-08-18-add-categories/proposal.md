## Why

`Concepto.categoria` is a free-form string today: retyping it on every concept means a single typo ("Creditos" vs. "Credito de cartera") becomes two permanently distinct, unrelated categories, and there is no way to rename a category everywhere it's used without editing every concept individually. The user wants categories to be a real, reusable entity with centralized editing, and wants the data model to support future grouping/analysis by category (not purely decorative), without building that analysis yet.

## What Changes

- **BREAKING**: `Concepto.categoria` (free-form string) is replaced by a many-to-many relationship to a new `Categoria` entity. The old field is dropped; existing string values are migrated into real `Categoria` rows and linked to their concepts.
- Add a `Categoria` entity per user: `nombre` (required), `emoji` (optional, must be one of a fixed curated set).
- Add full CRUD endpoints for categories: create, list, get, rename/update (including emoji), delete.
- Deleting a category silently unassigns it from any concept that had it — it is never blocked and never leaves a concept in an invalid state.
- Renaming or changing a category's emoji is immediately reflected everywhere that category is used, since the name/emoji live in one row, not duplicated per concept.
- `POST /concepts` and `PATCH /concepts/{id}` accept a list of category ids to assign (zero, one, or many); a concept's response includes its full list of assigned categories (id, nombre, emoji), not just ids.
- Categories remain global per user (not scoped by concept type) and remain optional on a concept, matching today's behavior.

## Capabilities

### New Capabilities
- `category-management`: CRUD for the `Categoria` entity itself (create, list, get, update, delete), independent of any specific concept.

### Modified Capabilities
- `budget-concepts`: concept creation/update/read behavior changes from a free-form category string to assigning zero or more real `Categoria` entities by id, with validation that referenced categories exist and belong to the user.

## Impact

- Backend only: new `Categoria` model + migration (schema change + one-time data migration of existing `concepts.categoria` string values), `app/schemas/concepto.py`, `app/services/concept_service.py`, `app/routers/concepts.py`, new `app/models/categoria.py`, `app/schemas/categoria.py`, `app/services/categoria_service.py`, `app/routers/categorias.py`.
- No frontend changes in this change — a separate frontend change will consume the new endpoints once this is applied.
- No analytics/reporting/grouping-by-category screens or endpoints — explicitly out of scope, left as future backlog.
