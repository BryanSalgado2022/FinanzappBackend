## 1. Model and migration

- [x] 1.1 Remove `saldo_disponible_inicial`, `saldo_disponible_fecha` from `User` in `app/models/user.py` (keep `ahorros`).
- [x] 1.2 Generate and review the alembic migration dropping those two columns.

## 2. Schema and endpoint removal

- [x] 2.1 Remove `saldo_disponible_inicial`/`saldo_disponible_fecha` from `UserRead`/`UserUpdate` in `app/schemas/user.py`.
- [x] 2.2 Remove `DisponibleRead` from `app/schemas/summary.py`.
- [x] 2.3 Remove the Disponible re-dating branch from `PATCH /users/me` in `app/routers/users.py` (keep the `ahorros` branch as-is).
- [x] 2.4 Remove `GET /summary/disponible` from `app/routers/summary.py`.
- [x] 2.5 Remove `disponible()`, `_sum_pagado`, `_sum_gastos_desde`, `_sum_abono_interes_desde` from `app/services/summary_service.py` (leave `_sum_abono_interes` used by the monthly summary untouched).

## 3. Tests

- [x] 3.1 Delete `tests/test_disponible.py`.
- [x] 3.2 Remove the Disponible-specific tests from `tests/test_users.py`, keep the `ahorros` tests.
- [x] 3.3 Run the full test suite and confirm it passes.
