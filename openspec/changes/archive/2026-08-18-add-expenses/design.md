## Context

See proposal.md - Why. `Categoria` (`app/models/categoria.py`) already exists as a reusable, user-scoped entity with `nombre`/`emoji`, currently assignable only to `Concepto` via the `ConceptoCategoria` link table. `summary_service.py::monthly_summary` currently derives `total_gastos` purely from `EntradaMensual.monto_planeado` joined through `Concepto`.

## Goals / Non-Goals

**Goals:**
- Let a `Gasto` share categories with `Concepto` without either entity depending on the other.
- Fold `Gasto` into the existing `monthly_summary` balance without changing its response shape.

**Non-Goals:**
- Category-level aggregation/reporting (explicit backlog, per proposal).
- Any change to `Concepto`, `EntradaMensual`, or their auto-generation behavior.

## Decisions

**`Gasto` is a standalone model, not a `TipoConcepto`.** `Concepto`/`EntradaMensual` model "one planned amount per month"; a `Gasto` is "N free-form amounts per month, each with its own date." Cramming it into `Concepto` would mean either a fake `EntradaMensual` per expense or a pile of nullable, `Gasto`-only columns on `Concepto`. A separate table with its own service/router (following the `Deudor` pattern) keeps both models simple. Balance integration is handled at the `summary_service` layer, not by making `Gasto` a `Concepto`.

**Categories via a new `GastoCategoria` link table, reusing `Categoria` as-is.** `ConceptoCategoria` is a link table keyed on `concepto_id`, so it can't also carry `gasto_id`. Adding a second link table (`gasto_id` + `categoria_id`, both `ondelete="CASCADE"`, mirroring `ConceptoCategoria`'s shape) lets `Gasto` and `Concepto` both point at the same `Categoria` rows without coupling the two entities to each other. Deleting a `Categoria` cascades the same way it already does for concepts: the assignment row disappears, the `Gasto` itself is untouched.

**`monthly_summary` sums `Gasto.monto` by `fecha`, not by creation time.** Mirrors `_sum_planeado`'s existing year/month filtering: a `select(func.coalesce(func.sum(Gasto.monto), 0)).where(Gasto.user_id == user_id, extract('year', Gasto.fecha) == anio, extract('month', Gasto.fecha) == mes)`, added to the existing deuda+gasto_fijo sum before computing `balance_neto`. This is what makes "registré tarde un gasto de hace 3 días" land in the correct historical month's balance instead of the current one.

**No new emoji set.** `Gasto` has no visual identity of its own (no `Gasto.emoji` field) — any emoji shown in the UI comes from its assigned `Categoria`, exactly like `Concepto` today.

## Risks / Trade-offs

- [Extracting year/month from a `date` column in SQL is slightly less portable than comparing whole dates] → Acceptable: `entrada_mensual` already stores `anio`/`mes` as separate ints for its own reasons, but `Gasto.fecha` is a single free-form date by design (per grilling), so extraction is the correct approach here; the project only targets PostgreSQL, where `extract()` is well-supported.
- [A user could unassign or delete a `Categoria` that's referenced by many expenses] → Already-accepted behavior for `Concepto`: the link row cascades away silently, never blocking the delete.
