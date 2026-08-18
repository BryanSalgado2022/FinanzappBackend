## Context

See proposal.md for motivation. Relevant current state:

- `Concepto.categoria: str | None` (table `concepts`) is the only thing being replaced. No other table references it.
- Real production data today has 9 distinct `(categoria, tipo)` combinations across the user's concepts (e.g. "Creditos", "Vivienda", "Sueldo") — small enough to migrate inline in a single Alembic migration, no batching needed.
- `SQLModel` models are plain classes with `table=True`; tests build the schema straight from model metadata (`SQLModel.metadata.create_all`), so a new model only needs to be added to `app/models/__init__.py` to be picked up by both the test suite and Alembic's autogeneration.
- Every existing user-owned entity (`Concepto`) is scoped by a direct `user_id` foreign key and every service function takes `user_id` explicitly rather than relying on session/global state — `Categoria` follows the same pattern.
- The router/service/schema split is consistent everywhere: models (SQLModel, DB-facing) → schemas (Pydantic `BaseModel`, request/response-facing) → service (business logic + custom exceptions) → router (HTTP mapping only). No existing precedent for a many-to-many relationship yet (all relationships so far are one-to-many via a single FK).

## Goals / Non-Goals

**Goals:**
- Land a normalized, queryable data model (`Categoria` + link table) that later analytics/grouping work can build on directly, without another migration.
- Keep `Concepto`'s create/update contract close in shape to today's (still a single JSON body), despite the underlying relationship becoming many-to-many.

**Non-Goals:**
- No analytics, grouping, or reporting endpoints — explicitly future work (proposal.md).
- No sharing of categories between users — each category is owned by exactly one user, same as concepts.
- No reordering/prioritization of a concept's categories — the list of assigned categories has no meaningful order beyond assignment.

## Decisions

**Link table `concepto_categoria` (plain many-to-many, no extra columns).**
A concept ↔ category assignment carries no data of its own (no "primary category" flag — the grilling session explicitly chose "show all emojis" over a primary-category concept), so the link table is just `(concepto_id, categoria_id)` with a composite primary key and `ON DELETE CASCADE` on both foreign keys. Cascading on the `concepto_id` side means deleting a concept doesn't leave orphaned link rows (mirrors the existing `monthly_entries` cascade pattern in `f115d9370a4b_cascade_delete_monthly_entries_with_.py`); cascading on the `categoria_id` side is what implements "deleting a category silently unassigns it" without any application-level cleanup code.

**Assignment shape on `ConceptoCreate`/`ConceptoUpdate`: `categoria_ids: list[int] | None`.**
- On create: omitted or empty list → no categories assigned (matches today's "no category" default).
- On update: `None` (the field omitted from the request) means "don't touch category assignments" — consistent with every other optional field on `ConceptoUpdate` today, which use `None`-means-unchanged semantics. To explicitly clear all categories, the client sends `categoria_ids: []`. This is the one asymmetry to document clearly in the API: `None` vs. `[]` are different requests on update, whereas for every other field on this schema `None` simply means "not provided."
- Validation (`categoria_ids` reference real categories owned by the current user) happens in the service layer, not a Pydantic validator, because it requires a DB lookup — same reasoning as why `cuota_inicial`'s cross-field checks are a `model_validator` (pure data shape) while ownership checks for `concepto_id` in `entry_service` happen in the service layer.

**"Find or create by name" is a category-service concern, not baked into the concept endpoints.**
The grilling session confirmed categories are created inline from the concept form, but the *concept* endpoints only ever accept `categoria_ids` (never raw names) — keeping `POST /concepts` and `PATCH /concepts/{id}` free of "maybe this is a new category" branching. Instead, `POST /categorias` is idempotent-by-name per user: creating a category with a `nombre` that already exists for that user (case-insensitive match) returns the existing category instead of erroring or duplicating. This lets the frontend implement "type a new name to create it inline" as a single unconditional `POST /categorias` call before assigning the id, without a separate "check if it exists first" round trip, and without ever producing duplicate categories differing only by case ("Vivienda" vs "vivienda").

**Emoji validated against a fixed, backend-defined set (not client-supplied, not open Unicode).**
A module-level constant (`ALLOWED_CATEGORIA_EMOJIS`) in `app/models/categoria.py` holds the curated list:
`💰 🏦 💳 🏠 🚗 🍽️ 💊 ✈️ 🎂 ❤️ 🎯 💡 💧 🛒 📅 📱`
(money, bank, card, home, car, food, health, travel, celebration, personal/love, goals, utilities, water, shopping, calendar/subscriptions, phone — chosen to cover the shapes already present in the user's real category names: Vivienda→🏠, Creditos/Prestamos→💳, Celular→📱, Sueldo/Salario/Primas→💰). Validated with a Pydantic `model_validator` on the category schemas (same mechanical pattern as `ConceptoCreate`'s validators), rejecting anything not in the set with a 422. Keeping the set backend-owned (not a free string) guarantees the frontend never needs to render an arbitrary/unknown glyph and keeps the "curated list" decision enforced in one place instead of duplicated client-side.

**Data migration lives inside the same Alembic revision as the schema change, using raw SQL via `op.get_bind()`.**
No existing migration in this project touches data (all prior ones are pure schema changes), so this is a new pattern, worth documenting: the single `upgrade()` function (1) creates `categorias` and `concepto_categoria`, (2) runs a raw-SQL data migration — for each distinct non-null `(user_id, categoria)` pair currently in `concepts`, insert one `categorias` row and link every matching `concepts.id` to it — using `op.get_bind().execute(sa.text(...))` rather than importing the SQLModel classes (importing application models from inside a migration is fragile once the models change shape in a later migration; raw SQL against the schema-as-it-exists-at-this-revision is the standard Alembic data-migration idiom), then (3) drops the `concepts.categoria` column. This keeps the migration self-contained and safe to run unattended — no separate manual data-fix step.

## Risks / Trade-offs

[Dropping `concepts.categoria` is irreversible once downgraded data is gone] → The migration's `downgrade()` re-adds the column but cannot losslessly reconstruct "one category per concept" from what could now be zero-or-many linked categories; document this explicitly in the migration's downgrade as a best-effort (picks one linked category's name arbitrarily, or null if none), since this project has no precedent of ever actually running a downgrade in production and the small real data volume makes this an acceptable, documented gap rather than engineering a lossless path.

[`None` vs. `[]` asymmetry on `ConceptoUpdate.categoria_ids` is a subtle API contract detail] → Call it out explicitly in the schema's field docstring/comment and in the README's endpoint table, the same way `cuota_inicial`'s immutability is called out today, so it isn't rediscovered as a bug later.

[Case-insensitive "find or create by name" on `POST /categorias` could surprise a caller expecting strict-create semantics] → Document the idempotent-by-name behavior directly in the endpoint's behavior (spec scenario) and README, since it's a deliberate simplification for the frontend's inline-creation flow, not a hidden side effect.
