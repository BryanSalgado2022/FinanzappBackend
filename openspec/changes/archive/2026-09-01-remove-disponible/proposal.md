## Why

The user tested Disponible and found the concept confusing to understand and explain ("va a generar mucha confusión") — the "accumulated since a baseline date" mental model didn't land. Removing it. `ahorros` (a simple, self-explanatory manually-set figure) stays — it wasn't the confusing part.

## What Changes

- **BREAKING**: `GET /summary/disponible` is removed entirely.
- `saldo_disponible_inicial` and `saldo_disponible_fecha` are removed from the user model, schemas, and the `PATCH /users/me` endpoint. `ahorros` is unaffected — it keeps its own independent get/set/clear behavior.
- The `available-balance` capability is removed entirely (no successor).

## Capabilities

### Removed Capabilities
- `available-balance`: Disponible tracking is removed in full — no replacement, per explicit user decision after testing it.

### Modified Capabilities
- `user-preferences`: drops the Disponible baseline fields and the re-dating requirement; `ahorros` and accent color are unaffected.

## Impact

- `app/models/user.py`: remove `saldo_disponible_inicial`, `saldo_disponible_fecha`.
- New alembic migration dropping those two columns (`ahorros` stays).
- `app/schemas/user.py`, `app/schemas/summary.py`: remove the corresponding fields and `DisponibleRead`.
- `app/routers/users.py`: remove the Disponible re-dating branch from `PATCH /users/me`.
- `app/routers/summary.py`: remove `GET /summary/disponible`.
- `app/services/summary_service.py`: remove `disponible()` and its Disponible-only helper functions (`_sum_pagado`, `_sum_gastos_desde`, `_sum_abono_interes_desde`) — `_sum_abono_interes` (used by the monthly summary) is unrelated and stays.
- `tests/test_disponible.py`: deleted. `tests/test_users.py`: remove the Disponible-specific tests, keep the `ahorros` ones.
