## 1. Deudor and Abono models and schemas

- [x] 1.1 Create `app/models/deudor.py`: `Deudor` (table `deudores`) with `id`, `user_id` (FK `users.id`, indexed), `nombre`, `monto_total: Decimal`, `fecha: date`, `garantia: str | None`, `activo: bool` (default `True`), `created_at`; `Abono` (table `abonos`) with `id`, `deudor_id` (FK `deudores.id`, indexed, `ondelete="CASCADE"`), `monto: Decimal`, `fecha: date`, `created_at`
- [x] 1.2 Register `Deudor` and `Abono` in `app/models/__init__.py`
- [x] 1.3 Create `app/schemas/deudor.py`: `DeudorCreate` (`nombre`, `monto_total`, `fecha` required; `garantia` optional), `DeudorUpdate` (all fields optional including `activo`), `DeudorRead` (all fields plus `saldo_restante`); `AbonoCreate` (`monto`, `fecha` required), `AbonoRead` (`id`, `monto`, `fecha`)

## 2. Deudor and Abono service and router

- [x] 2.1 Create `app/services/deudor_service.py`: `DeudorNotFoundError`, `AbonoNotFoundError`, `create_deudor`, `list_deudores`, `get_deudor`, `update_deudor`, `delete_deudor`, `saldo_restante(session, deudor)` (mirroring `concept_service.py::saldo_restante`'s query shape, no `cuota_inicial`-style wrinkle), `create_abono`, `list_abonos`, `delete_abono` (each abono function takes `user_id` + `deudor_id` and resolves the parent `Deudor` first, per design.md's ownership pattern)
- [x] 2.2 Create `app/routers/deudores.py`: `POST /deudores`, `GET /deudores`, `GET /deudores/{id}`, `PATCH /deudores/{id}`, `DELETE /deudores/{id}`, `POST /deudores/{id}/abonos`, `GET /deudores/{id}/abonos`, `DELETE /deudores/{id}/abonos/{abono_id}` — same auth/ownership/404/422 pattern as `app/routers/entries.py`; `_to_read` for a debtor computes `saldo_restante` via the service helper
- [x] 2.3 Register the new router in `app/main.py`

## 3. Migration

- [x] 3.1 Generate the Alembic revision (schema only: create `deudores` and `abonos` tables) via `docker compose exec api alembic revision --autogenerate -m "add deudores and abonos"`, restarting the `api` container first if model code changed since its last restart

## 4. Tests

- [x] 4.1 `tests/test_deudores.py`: create with required fields only, create with garantia, list scoped to owner, get scoped to owner (404 for another user's debtor), update each field independently, close a debtor with a nonzero balance, delete a debtor cascades its abonos, `saldo_restante` computation (no abonos = full monto_total; partial abonos; abonos summing to monto_total = zero)
- [x] 4.2 `tests/test_abonos.py`: create an abono and confirm it reduces `saldo_restante`, create an abono against another user's debtor returns 404, list abonos scoped to owner, delete an abono restores its amount to `saldo_restante`, delete an abono from another user's debtor returns 404
- [x] 4.3 Run the full suite (`docker compose exec -T api python -m pytest -q`) and confirm no regressions

## 5. Docs

- [x] 5.1 Update `README.md`'s endpoint table with the 8 new `/deudores` endpoints
- [x] 5.2 Add a bullet to "Decisiones clave a recordar" covering: `Deudor` is the mirror image of a `deuda` concept (money owed TO the user) but fully standalone; `saldo_restante` is computed the same way as debt concepts (never stored); abonos have no update endpoint (delete + recreate); no summary endpoint by design

## 6. Manual verification

- [x] 6.1 Via curl against the running docker-compose backend: create a debtor with just required fields, create one with garantia, record two abonos against it and confirm `saldo_restante` decreases correctly, delete one abono and confirm the balance is restored, mark the debtor `activo: false` while it still has a balance and confirm it's accepted, delete the debtor and confirm its abonos are gone too (via a subsequent 404 on the abonos list, or a direct DB check)
