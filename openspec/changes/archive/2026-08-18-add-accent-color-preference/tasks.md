## 1. Model and migration

- [x] 1.1 Add `ALLOWED_ACCENT_COLORS = ("verde", "azul", "morado", "rosa", "naranja", "amarillo", "rojo", "turquesa", "gris")` and a `color_acento: str | None` field to `User` in `app/models/user.py`
- [x] 1.2 Generate the Alembic migration (`alembic revision --autogenerate`) and review it before applying

## 2. Schema and router

- [x] 2.1 Create `app/schemas/user.py`: `UserRead` (id, email, name, `color_acento`), `UserUpdate` (`color_acento: str | None = None`, validated against `ALLOWED_ACCENT_COLORS` via `model_validator` when non-null)
- [x] 2.2 Create `app/routers/users.py`: `GET /users/me` returns the authenticated user's `UserRead`; `PATCH /users/me` updates `color_acento` only if the field was present in the request body (use `payload.model_fields_set`, not just the deserialized value, to distinguish "omitted" from "explicit null")
- [x] 2.3 Register the router in `app/main.py`

## 3. Tests

- [x] 3.1 `tests/test_users.py`: `GET /users/me` returns `color_acento: null` by default; `PATCH` sets a valid color and it's reflected on subsequent `GET`; `PATCH` with an invalid identifier returns 422 and leaves the stored value unchanged; `PATCH` with `color_acento: null` clears a previously set color; `PATCH` with an empty body leaves an existing color untouched; requests are scoped to the authenticated user (no cross-user leakage)

## 4. Docs

- [x] 4.1 Add the `/users/me` endpoint table rows and a "Decisiones clave a recordar" bullet to `README.md`, documenting the allowed color set and the omitted-vs-null PATCH semantics
