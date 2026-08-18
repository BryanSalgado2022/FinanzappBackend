## 1. Tarea model and schema

- [x] 1.1 Create `app/models/tarea.py`: `Tarea` (table `tareas`) with `id`, `user_id` (FK `users.id`, indexed), `titulo`, `emoji: str | None`, `fecha: date | None`, `hora: time | None`, `nota: str | None`, `completada: bool` (default `False`), `created_at`; module-level `ALLOWED_TAREA_EMOJIS` constant with a curated ~20-emoji reminder-oriented set (checkmark, clock, bell, phone, document, etc.), separate from `ALLOWED_CATEGORIA_EMOJIS`
- [x] 1.2 Register `Tarea` in `app/models/__init__.py`
- [x] 1.3 Create `app/schemas/tarea.py`: `TareaCreate` (`titulo` required; optional `emoji`, `fecha`, `hora`, `nota`), `TareaUpdate` (all fields optional, including `completada`), `TareaRead` (`id`, `titulo`, `emoji`, `fecha`, `hora`, `nota`, `completada`, `vencida`), with a validator on Create/Update rejecting any `emoji` not in `ALLOWED_TAREA_EMOJIS`

## 2. Tarea service and router

- [x] 2.1 Create `app/services/tarea_service.py`: `TareaNotFoundError`, `create_tarea`, `list_tareas`, `get_tarea`, `update_tarea`, `delete_tarea`, and `es_vencida(fecha, completada)` mirroring `entry_service.py::es_vencida`'s pattern (returns `False` if `fecha` is `None` or `completada` is `True`, else `fecha < date.today()`)
- [x] 2.2 Create `app/routers/tareas.py`: `POST /tareas`, `GET /tareas`, `GET /tareas/{id}`, `PATCH /tareas/{id}`, `DELETE /tareas/{id}` — same auth/ownership/404/422 pattern as `app/routers/categorias.py`; `_to_read` computes `vencida` via the service helper
- [x] 2.3 Register the new router in `app/main.py`

## 3. Migration

- [x] 3.1 Generate the Alembic revision (schema only: create `tareas` table) via `docker compose exec api alembic revision --autogenerate -m "add tareas"`, restarting the `api` container first if model code changed since its last restart

## 4. Tests

- [x] 4.1 `tests/test_tareas.py`: create with just a title, create with all fields, reject invalid emoji, list scoped to owner, get scoped to owner (404 for another user's task), update each field independently, toggle `completada`, delete scoped to owner (404 for another user's task), `vencida` computation (past date + not completed = true; past date + completed = false; no date = false; future date = false)
- [x] 4.2 Run the full suite (`docker compose exec -T api python -m pytest -q`) and confirm no regressions

## 5. Docs

- [x] 5.1 Update `README.md`'s endpoint table with the 5 new `/tareas` endpoints
- [x] 5.2 Add a bullet to "Decisiones clave a recordar" covering: tasks are a standalone entity unrelated to concepts, the separate fixed emoji set, the computed (not stored) `vencida` flag, and that recurrence/frequency is deliberately not implemented yet (pending the future Agenda calendar view)

## 6. Manual verification

- [x] 6.1 Via curl against the running docker-compose backend: create a task with just a title, create one with a past date and confirm `vencida: true`, mark it `completada` and confirm `vencida` becomes `false`, update individual fields, attempt an invalid emoji and confirm 422, delete a task and confirm it's gone from the list
