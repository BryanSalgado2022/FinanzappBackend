## MODIFIED Requirements

### Requirement: Monthly net balance summary
The system SHALL provide, for a given user/year/month, a summary that computes `balance_neto` as the sum of `monto_planeado` across that user's active `ingreso` concepts for that month, minus the sum of `monto_planeado` across that user's active `deuda` and `gasto_fijo` concepts for that month, minus the sum of that user's `Gasto.monto` whose `fecha` falls in that month.

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
