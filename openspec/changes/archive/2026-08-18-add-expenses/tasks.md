## 1. Model and migration

- [x] 1.1 Create `app/models/gasto.py` with `Gasto` (`id`, `user_id` FK indexed, `monto: Decimal`, `fecha: date`, `descripcion: str`, `created_at`) and `GastoCategoria` link table (`gasto_id`+`categoria_id` PK, both `ondelete="CASCADE"`)
- [x] 1.2 Register `Gasto`/`GastoCategoria` in `app/models/__init__.py`
- [x] 1.3 Generate the Alembic migration (`alembic revision --autogenerate`) and review it before applying

## 2. Schemas and service

- [x] 2.1 Create `app/schemas/gasto.py`: `GastoCreate`, `GastoUpdate`, `GastoRead` (including assigned `categorias`)
- [x] 2.2 Create `app/services/gasto_service.py`: create, get, list (filtered by `anio`/`mes`), update, delete, all `user_id`-scoped with a `GastoNotFoundError`
- [x] 2.3 Add a helper to sum a user's `Gasto.monto` for a given year/month (mirrors `_sum_planeado`'s filtering shape)

## 3. Router

- [x] 3.1 Create `app/routers/gastos.py`: `POST /gastos`, `GET /gastos` (with `anio`/`mes` query filter), `GET /gastos/{id}`, `PATCH /gastos/{id}`, `DELETE /gastos/{id}`
- [x] 3.2 Register the router in `app/main.py`

## 4. Balance integration

- [x] 4.1 Update `app/services/summary_service.py::monthly_summary` to subtract the year/month `Gasto` sum from `total_gastos`

## 5. Tests

- [x] 5.1 `tests/test_gastos.py`: CRUD, ownership scoping (404 across users), category assignment/reassignment, year/month filtering
- [x] 5.2 Update/add a test asserting `monthly_summary` reflects a variable expense dated in the requested month, and is unaffected by one dated outside it

## 6. Docs

- [x] 6.1 Add the `/gastos` endpoint table rows and a "Decisiones clave a recordar" bullet to `README.md`, following the style of the `Tarea`/`Deudor` entries
