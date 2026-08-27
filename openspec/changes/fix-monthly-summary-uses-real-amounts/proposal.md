## Why

The monthly summary ("Balance del mes") sums `monto_planeado` for every entry regardless of paid status. A user reported the exact gap this causes: they registered an income entry planned at 10.000.000, then marked it paid with an actual `monto_pagado` of 9.500.000 (less arrived than expected) — the summary kept showing 10.000.000 as if the full planned amount had come in. The same gap applies to `deuda`/`gasto_fijo` entries paid for less (or more) than planned. This is the same real-vs-planned distinction already correctly handled by the newly added Disponible feature (`add-available-balance`) — the monthly summary should not lag behind it.

## What Changes

- `monthly_summary`'s `total_ingresos` and `total_gastos` now use each entry's `monto_pagado` when `pagado` is true, falling back to `monto_planeado` only for entries not yet paid (there is no other value to use for those).
- No change to which entries are included (still every entry for the requested `anio`/`mes`, paid or not) — only which amount field is summed per entry.

## Capabilities

### Modified Capabilities
- `monthly-budget`: "Monthly net balance summary" changes to sum the real paid amount for paid entries instead of always using the planned amount.

## Impact

- `app/services/summary_service.py`: `_sum_planeado` (or a renamed/adjacent function) changes its per-entry amount expression from `monto_planeado` to `CASE WHEN pagado THEN monto_pagado ELSE monto_planeado END`.
- No schema/migration change — both fields already exist on `EntradaMensual`.
