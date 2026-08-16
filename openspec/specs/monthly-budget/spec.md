# monthly-budget Specification

## Purpose
Tracks what a user plans and actually pays each month for every concept, and turns that into a single monthly balance figure — the automated equivalent of the "GASTOS AL MES" / "CUANTO QUEDA" rows in their spreadsheet.

## Requirements

### Requirement: Monthly entry per concept
The system SHALL track, for each concept and each year/month, a `monto_planeado` (planned amount), an optional `monto_pagado` (actual amount paid, nullable until paid), and a `pagado` status.

#### Scenario: Record a planned amount
- **WHEN** a user sets the planned amount for a concept in a given year/month
- **THEN** the system saves that `monto_planeado` for that concept/year/month

#### Scenario: Record a payment that differs from the plan
- **WHEN** a user marks a monthly entry as paid with a `monto_pagado` different from its `monto_planeado`
- **THEN** the system saves both values independently and marks the entry `pagado`

#### Scenario: Only one entry per concept per month
- **WHEN** a monthly entry already exists for a given concept, year, and month
- **THEN** the system updates that existing entry instead of creating a duplicate

### Requirement: Auto-generate future monthly entries
The system SHALL automatically create monthly entries for the remaining months of the current calendar year, using the most recently used planned amount, when a recurring concept (`deuda` or `gasto_fijo` that is active) is created or its planned amount is edited.

#### Scenario: Creating a recurring concept generates the rest of the year
- **WHEN** a user creates an active `gasto_fijo` concept with a planned monthly amount in month M of the current year
- **THEN** the system creates monthly entries with that planned amount for months M through December of the current year

#### Scenario: Editing a planned amount updates future months
- **WHEN** a user changes the planned amount for a concept's current month
- **THEN** the system applies that new planned amount to that month's entry and to the auto-generated entries for the remaining future months, without altering already-recorded past months

#### Scenario: Finished concepts are not auto-generated
- **WHEN** a concept has been marked finished
- **THEN** the system does not generate further monthly entries for it

### Requirement: Monthly net balance summary
The system SHALL provide, for a given user/year/month, a summary that computes `balance_neto` as the sum of `monto_planeado` across that user's active `ingreso` concepts for that month, minus the sum of `monto_planeado` across that user's active `deuda` and `gasto_fijo` concepts for that month.

#### Scenario: Positive balance
- **WHEN** a user's planned income for a month exceeds their planned debts and fixed expenses for that month
- **THEN** the summary reports a positive `balance_neto` equal to that difference

#### Scenario: Negative balance
- **WHEN** a user's planned debts and fixed expenses for a month exceed their planned income for that month
- **THEN** the summary reports a negative `balance_neto` equal to that difference

#### Scenario: Month with no entries
- **WHEN** a user has no monthly entries at all for the requested year/month
- **THEN** the summary reports a `balance_neto` of zero rather than an error

### Requirement: Auto-generation uses the amortization schedule for amortized debts
The system SHALL, for a debt concept with amortization data, generate monthly entries for its entire amortization schedule (one entry per installment, spanning beyond the current calendar year if `numero_cuotas` requires it) at creation time, using each installment's fixed amount from the schedule instead of the copy-last-amount-forward behavior used for other recurring concepts.

#### Scenario: Multi-year debt generates entries beyond the current year
- **WHEN** a debt is created with `numero_cuotas` greater than the number of months remaining in the current calendar year
- **THEN** the system generates monthly entries continuing into the following year(s) until all installments have an entry, not just through December of the current year

#### Scenario: Generated amounts follow the schedule, not a flat copy
- **WHEN** an amortized debt's fixed installment is computed
- **THEN** every auto-generated entry for that debt uses that fixed installment amount as `monto_planeado`, consistent across all its months

#### Scenario: Non-amortized recurring concepts are unaffected
- **WHEN** a `deuda` concept without amortization data, or a `gasto_fijo` concept, is created or edited
- **THEN** auto-generation continues to behave exactly as before this change (copy-last-amount-forward through December of the current year)
