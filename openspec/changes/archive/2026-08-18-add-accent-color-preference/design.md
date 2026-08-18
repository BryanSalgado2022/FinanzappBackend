## Context

See proposal.md - Why. `app/models/categoria.py::ALLOWED_CATEGORIA_EMOJIS` is the established pattern for a backend-owned curated set validated in a Pydantic schema.

## Goals / Non-Goals

**Goals:**
- Store and serve a validated accent-color identifier per user, with no color/CSS knowledge in the backend.

**Non-Goals:**
- Any other preference (theme, density, etc.) - this change is accent color only, per proposal.
- Deriving or storing actual hex/CSS values - that's the frontend's job in a follow-up change.

## Decisions

**Allowed set: 9 identifiers, plain color-name strings.** `ALLOWED_ACCENT_COLORS = ("verde", "azul", "morado", "rosa", "naranja", "amarillo", "rojo", "turquesa", "gris")`, defined in `app/models/user.py` next to `User`, mirroring `ALLOWED_CATEGORIA_EMOJIS`'s placement convention (constant colocated with the model it constrains). Plain names (not hex codes) keep the contract stable even if the frontend later retunes a color's exact shade - the identifier's meaning ("this user picked the purple option") doesn't change just because purple's hex value gets adjusted for contrast.

**`color_acento: str | None` on `User`, nullable, no default value forced.** `None` is a first-class, valid state ("use the app default"), not merely "not yet set" - the "clear back to default" requirement (see spec) needs a way to represent "no preference" distinct from any of the 9 colors, and `None` is the natural fit.

**`GET /users/me` / `PATCH /users/me` under a new `users` router**, following the exact shape of every existing router: `Depends(get_current_user)` resolves the account from the JWT, no `user_id` path/query parameter ever accepted (the spec's "always the authenticated user, never another's" requirement is enforced structurally, not by a runtime check that could be forgotten).

**Validation via Pydantic `model_validator`, matching `CategoriaUpdate`'s style**: `UserUpdate.color_acento: str | None = None` where `None` sent explicitly means "clear," validated against `ALLOWED_ACCENT_COLORS` when non-null, rejecting anything else with a 422 - not caught in a router-level `try/except`, but via the schema itself so FastAPI's own validation error path handles it uniformly with every other curated-set field in the app.

## Risks / Trade-offs

- [Pydantic can't tell "field omitted from the request body" apart from "field explicitly sent as `null`" unless the router checks `model_fields_set`, and this schema needs both to mean different things: omitted = don't touch, explicit `null` = clear back to default] → Mitigation: the router reads `payload.model_fields_set` (not just the deserialized value) to decide whether `color_acento` was present in the request at all before applying it, the same class of omitted-vs-explicit distinction `ConceptoUpdate.categoria_ids` already established for a list field - call this out explicitly in tasks.md so it isn't silently mishandled as "any None means don't touch."
