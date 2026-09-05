## 1. Model and migration

- [x] 1.1 Create `app/models/aporte_ahorro.py`: `TipoAporte` enum (`APORTE="aporte"`, `RETIRO="retiro"`), `AporteAhorro` model (table `aportes_ahorro`): `id`, `user_id` (FK `users.id`, index), `monto` (Decimal, max_digits=14, decimal_places=2), `tipo`, `fecha`, `created_at`.
- [x] 1.2 Remove `ahorros` from `User` in `app/models/user.py`.
- [x] 1.3 Register `AporteAhorro`/`TipoAporte` in `app/models/__init__.py`.
- [x] 1.4 Generate an Alembic migration that (a) creates the `tipoaporte` enum + `aportes_ahorro` table, (b) data-migrates every user's non-null `ahorros` into one `AporteAhorro` row (`tipo='aporte'`, `fecha=`today), (c) drops the `ahorros` column from `users`. Write a lossy-but-documented downgrade per design.md. Apply it.

## 2. Schemas

- [x] 2.1 Create `app/schemas/ahorro.py`: `AporteAhorroCreate { monto: Decimal, fecha: date, tipo: TipoAporte }`, `AporteAhorroRead { id, monto, fecha, tipo, created_at }`.
- [x] 2.2 In `app/schemas/user.py`, change `UserRead.ahorros` to non-nullable `Decimal`; remove `ahorros` from `UserUpdate`.

## 3. Service logic

- [x] 3.1 Create `app/services/ahorro_service.py`: `create_aporte(session, user_id, monto, fecha, tipo)`, `list_aportes(session, user_id)` (ordered by `fecha` descending), `delete_aporte(session, user_id, aporte_id)` (raise a not-found error if missing or not owned), `saldo_ahorros(session, user_id) -> Decimal` (sum aporte minus sum retiro, default zero).

## 4. Routers

- [x] 4.1 Create `app/routers/ahorros.py`: `POST /ahorros`, `GET /ahorros`, `DELETE /ahorros/{aporte_id}`, all scoped to the authenticated user.
- [x] 4.2 Register the new router in `app/main.py`.
- [x] 4.3 In `app/routers/users.py`, add a `session` dependency to `get_me`, compute `ahorros` via `ahorro_service.saldo_ahorros` in both `get_me` and `update_me`'s `_to_read`, and remove the `ahorros` PATCH branch from `update_me`.

## 5. Tests

- [x] 5.1 Add ledger tests: recording an aporte/retiro, listing ordered by fecha descending, deleting an entry, cross-user 404 scoping on delete.
- [x] 5.2 Add running-balance tests: mix of aporte/retiro computes correctly, zero balance with no entries.
- [x] 5.3 Add a test confirming `PATCH /users/me` with an `ahorros` field either rejects it or silently ignores it (whichever `extra="ignore"`'s default Pydantic behavior produces) and does not change the computed balance.
- [x] 5.4 Add a test confirming recording a retiro/aporte does not change `GET /summary` for the same month (explicitly asserting the no-linkage constraint).
- [x] 5.5 Run the full backend test suite and confirm everything passes.
