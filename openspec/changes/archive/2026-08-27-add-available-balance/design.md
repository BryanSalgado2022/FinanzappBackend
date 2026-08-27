## Context

`EntradaMensual` already has a `fecha_pago` column (nullable, set when the entry is marked paid) — see `app/models/entrada_mensual.py` — separate from `anio`/`mes`, which describe which month the entry belongs to, not when it was actually paid. `summary_service.py`'s existing monthly summary never uses `fecha_pago`; it sums `monto_planeado` for a single `anio`/`mes` regardless of paid status. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- A single running total, queryable in one request, correct regardless of how many months/entries have accumulated.
- No new tables beyond the three nullable `users` columns — reuse `EntradaMensual.fecha_pago`, `Gasto.fecha`, `Abono.fecha`/`interes` (the last from the sibling `add-abono-interest` change) as-is.

**Non-Goals:**
- Any change to the existing monthly summary endpoint/computation.
- Automatically adjusting `ahorros` (explicitly rejected during grilling — stays user-managed).

## Decisions

**Use `fecha_pago`, not `anio`/`mes`, for the date filter on `EntradaMensual`.** An entry's `anio`/`mes` says which month it's *for*, not when it was actually paid — a January bill paid on February 3rd should count toward Disponible as of February 3rd, not January. `fecha_pago` is set precisely when `pagado` becomes true (existing behavior, unchanged by this proposal), so filtering `fecha_pago >= saldo_disponible_fecha AND pagado = true` is both correct and requires no new column.

**Sum `monto_pagado`, never `monto_planeado`.** `entry_service._save_entry` (`app/services/entry_service.py:97-124`) already guarantees `monto_pagado` is never null once `pagado` is true — it defaults to `monto_planeado` server-side when the caller marks an entry paid without specifying an actual amount, exactly the same invariant `saldo_restante`'s amortization math already relies on. This means Disponible needs no `COALESCE`: `monto_pagado` is always populated correctly for any paid entry. This matters because the *existing* `monthly_summary` ("Balance del mes") sums `monto_planeado` unconditionally, so it does **not** reflect a partial payment (e.g. planned 100.000, actually paid 50.000 still shows as 100.000 spent there) — Disponible must not repeat that gap, since "how much do I actually have" is precisely the question `monto_planeado` cannot answer.

**Query shape**: one function in a new or existing service (`summary_service.py` is a reasonable home, or a new `available_balance_service.py` given it's a distinct capability) that runs four scoped sums against the authenticated user's data — paid `ingreso` entries, paid `deuda`/`gasto_fijo` entries, `Gasto` rows, and `Abono.interes` (joined through `Deudor` to scope by `user_id`, since `Abono` has no direct `user_id`) — each filtered by its own date column `>= saldo_disponible_fecha`, then combines: `saldo_disponible_inicial + ingresos_pagados + intereses_abonos - gastos_pagados_deuda_fijo - gastos_variables`.

**Re-baselining on every edit** (already specified in the `user-preferences` delta): handled in the `UserUpdate` PATCH handler — when `saldo_disponible_inicial` is present in `model_fields_set`, force `saldo_disponible_fecha = date.today()` server-side rather than accepting a client-supplied date, exactly mirroring the existing `model_fields_set`-based partial-update pattern already used for `color_acento`.

**Endpoint shape**: `GET /summary/disponible` (or nested under an existing summary router) returning `{ disponible: str | None, saldo_disponible_fecha: date | None }` — `None` when unset, so the frontend can distinguish "not configured yet" from "configured and currently zero."

## Risks / Trade-offs

- [Risk] A user who never marks entries paid (leaves everything pending) would see Disponible stay flat at their baseline forever, which is accurate but could look like a bug. → Mitigation: this is the correct behavior per the spec (unpaid entries never count) — no code mitigation needed, just something to be aware of if support questions come up.
- [Risk] Four separate scoped-sum queries (vs. one combined query) is slightly less efficient than a single query, but at MVP personal-finance scale (a handful of concepts/gastos/abonos per user) this is negligible, consistent with the same assumption already made elsewhere in this codebase (e.g. `useDashboardConcepts`'s per-concept query fan-out).
