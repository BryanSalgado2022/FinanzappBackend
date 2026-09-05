## MODIFIED Requirements

### Requirement: Monthly net balance summary
The system SHALL provide, for a given user/year/month, a summary that computes `balance_neto` as the sum, across that user's active `ingreso` concepts for that month, of each entry's `monto_pagado` when paid or `monto_planeado` when not yet paid, plus the sum of `interes` across that user's abonos whose `fecha` falls in that month, plus the sum of `interes` across that user's paid debtor installments whose payment date falls in that month, minus the same paid-or-planned sum across that user's active `deuda` and `gasto_fijo` concepts for that month, minus the sum of that user's `Gasto.monto` whose `fecha` falls in that month.

#### Scenario: Positive balance
- **WHEN** a user's planned income for a month exceeds their planned debts, fixed expenses, and variable expenses for that month
- **THEN** the summary reports a positive `balance_neto` equal to that difference

#### Scenario: Negative balance
- **WHEN** a user's planned debts, fixed expenses, and variable expenses for a month exceed their planned income for that month
- **THEN** the summary reports a negative `balance_neto` equal to that difference

#### Scenario: Month with no entries
- **WHEN** a user has no monthly entries and no variable expenses at all for the requested year/month
- **THEN** the summary reports a `balance_neto` of zero rather than an error

#### Scenario: Variable expenses reduce the balance
- **WHEN** a user records a variable expense with a `fecha` in the requested year/month
- **THEN** the summary's `total_gastos` and resulting `balance_neto` reflect that expense's `monto`, using the expense's own `fecha` rather than when it was recorded

#### Scenario: Abono interest contributes to total income
- **WHEN** a user records an abono with an `interes` value against any of their debtors, with a `fecha` in the requested year/month
- **THEN** the summary's `total_ingresos` and resulting `balance_neto` include that `interes` amount, using the abono's own `fecha` rather than when it was recorded

#### Scenario: Abono principal does not affect the summary
- **WHEN** a user records an abono with no `interes` value, or an abono whose `interes` is zero
- **THEN** the summary is unaffected by that abono's `monto`

#### Scenario: Unpaid entries use the planned amount
- **WHEN** a user has an entry for the requested month that is not yet paid
- **THEN** the summary uses its `monto_planeado`, exactly as before this change

#### Scenario: Paid entries use the actual amount, even when it differs from the plan
- **WHEN** a user has an entry for the requested month marked paid with a `monto_pagado` different from its `monto_planeado`
- **THEN** the summary uses `monto_pagado`, not `monto_planeado`, for that entry

#### Scenario: An underpaid income entry does not overstate the summary
- **WHEN** a user marks an `ingreso` entry paid with `monto_pagado` less than its `monto_planeado`
- **THEN** the summary's `total_ingresos` and `balance_neto` reflect the smaller amount actually received, not the originally planned amount

#### Scenario: A paid debtor installment's interest contributes to total income
- **WHEN** a user marks one of their amortized debtor's scheduled installments paid, and its recorded payment date falls in the requested year/month
- **THEN** the summary's `total_ingresos` and resulting `balance_neto` include that installment's `interes` amount

#### Scenario: An unpaid debtor installment does not affect the summary
- **WHEN** an amortized debtor has a scheduled installment that is not yet marked paid
- **THEN** the summary is unaffected by that installment, regardless of its scheduled year/month

#### Scenario: A debtor installment's principal does not affect the summary
- **WHEN** a user marks a debtor installment paid
- **THEN** the summary is affected only by that installment's `interes`, not by the principal portion of the amount paid
