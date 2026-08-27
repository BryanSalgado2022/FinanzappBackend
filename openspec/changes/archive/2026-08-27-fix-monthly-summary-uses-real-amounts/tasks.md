## 1. Service logic

- [x] 1.1 In `app/services/summary_service.py`'s `_sum_planeado`, change the summed expression from `EntradaMensual.monto_planeado` to `CASE WHEN EntradaMensual.pagado THEN EntradaMensual.monto_pagado ELSE EntradaMensual.monto_planeado END` (via SQLAlchemy `case()`), for both the `ingreso` and `deuda`/`gasto_fijo` calls.

## 2. Tests

- [x] 2.1 Add tests in `tests/test_entries_summary.py`: an unpaid entry still uses `monto_planeado`; a paid entry with `monto_pagado` different from `monto_planeado` uses `monto_pagado`; an underpaid `ingreso` entry (paid for less than planned) reduces `total_ingresos`/`balance_neto` accordingly, reproducing the exact scenario reported (planned 10.000.000, paid 9.500.000).
- [x] 2.2 Run the full test suite and confirm it passes, including the pre-existing `test_monthly_summary_matches_verified_spreadsheet_numbers` and other summary tests that assume unpaid entries (should be unaffected).
