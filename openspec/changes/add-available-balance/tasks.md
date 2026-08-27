## 1. Model and migration

- [x] 1.1 Add `ahorros: Decimal | None`, `saldo_disponible_inicial: Decimal | None`, `saldo_disponible_fecha: date | None` to `User` in `app/models/user.py`.
- [x] 1.2 Generate and review the alembic migration adding the three nullable columns to `users`.

## 2. Schema and preference updates

- [x] 2.1 Add the three fields to `UserRead` in `app/schemas/user.py`.
- [x] 2.2 Add `ahorros`/`saldo_disponible_inicial` to `UserUpdate` (no `saldo_disponible_fecha` field on the input schema — it's never client-supplied).
- [x] 2.3 In the `PATCH /users/me` handler, when `saldo_disponible_inicial` is present in `payload.model_fields_set`, set `saldo_disponible_fecha = date.today()` alongside it.

## 3. Disponible computation

- [x] 3.1 Add a service function computing Disponible per design.md's formula (paid ingreso entries' `monto_pagado` + abono interest - paid deuda/gasto_fijo entries' `monto_pagado` - `Gasto.monto`, all filtered by their own date column `>= saldo_disponible_fecha`, plus `saldo_disponible_inicial`), returning `None` when `saldo_disponible_fecha` is unset. Sum `monto_pagado`, never `monto_planeado` - see design.md.
- [x] 3.2 Add `GET /summary/disponible` (or equivalent path) returning `{ disponible: str | None, saldo_disponible_fecha: date | None }`.

## 4. Tests

- [x] 4.1 Add tests: setting/clearing `ahorros`; setting `saldo_disponible_inicial` records today's date; setting it again replaces both value and date.
- [x] 4.2 Add tests for the Disponible endpoint: unset baseline returns `None`; paid ingreso/deuda/gasto_fijo entries and Gasto and abono interest each contribute correctly; entries before the baseline date are excluded; unpaid entries are excluded; per-user scoping; a partial payment (`monto_pagado` less than `monto_planeado`) only reduces Disponible by the amount actually paid, not the planned amount.
- [x] 4.3 Run the full test suite and confirm it passes.
