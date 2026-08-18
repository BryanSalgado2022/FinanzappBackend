## Context

See proposal.md for motivation. Relevant current state:

- `app/models/categoria.py` is the closest existing pattern: a simple per-user entity with a fixed, backend-owned emoji allowlist validated via a Pydantic `model_validator`, plus matching `*_service.py`/`*.py` router modules. `Tarea` follows the same shape.
- `app/services/entry_service.py::es_vencida(dia_vencimiento, anio, mes, pagado)` is the existing pattern for a computed "overdue" flag: never stored, computed at read time from a date comparison plus a completion/paid flag, always `False` when there's nothing to be overdue against.
- No existing entity in this codebase has both an optional `date` and an optional `time` field independently — `Concepto`'s `dia_vencimiento` is an integer day-of-month, not a real date. This is the first use of SQLModel's `date`/`time` column types.

## Goals / Non-Goals

**Goals:**
- Ship a fully standalone, self-contained entity — no foreign keys to or from `Concepto`, `Categoria`, or any other existing table.

**Non-Goals:**
- No recurrence/frequency field or generation logic. This was deliberately scoped out during grilling: without the future "Agenda" calendar view, there is nowhere to meaningfully display repeated future instances, and building the field now risks a throwaway shape once that view exists. Explicitly deferred, not forgotten — do not silently reintroduce it later without revisiting this decision.
- No task count, summary, or Dashboard integration of any kind.

## Decisions

**A separate, task-specific emoji allowlist (`ALLOWED_TAREA_EMOJIS`), not the existing `ALLOWED_CATEGORIA_EMOJIS`.**
The user's reference screenshot showed a reminder-oriented icon set (clock, bell, phone, document, checkmark) meaningfully different from the finance-oriented category set. Keeping two separate module-level constants (in `app/models/categoria.py` and `app/models/tarea.py` respectively) costs nothing and keeps each set curated for its own context, consistent with the reasoning already recorded in `add-categories`'s design.md for why the category set is fixed and backend-owned in the first place.

**`vencida` is computed the same way as `EntradaMensual.vencida`, not stored.**
`vencida = fecha is not None and fecha < today and not completada`. Storing it would require a background job or write-time recomputation to stay correct as "today" changes; computing it at read time (as the router builds `TareaRead`) is free and can never go stale, matching the existing convention.

**No uniqueness or find-or-create semantics for `titulo`.**
Unlike `Categoria.nombre` (which needed find-or-create for the frontend's inline-creation flow), a task's title is free-form and expected to repeat naturally ("Pagar la luz" every month is a reasonable thing to type more than once) — every `POST /tareas` call creates a new row, no dedup logic.

## Risks / Trade-offs

[No recurrence means a genuinely recurring reminder must be manually recreated each time] → Accepted per the Non-Goals above; the alternative (building recurrence now with nowhere to surface it) is worse. Revisit when the Agenda calendar view is scoped.
