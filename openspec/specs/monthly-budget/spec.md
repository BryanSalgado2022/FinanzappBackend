# monthly-budget Specification

## Purpose
Tracks what a user plans and actually pays each month for every concept, and turns that into a single monthly balance figure — the automated equivalent of the "GASTOS AL MES" / "CUANTO QUEDA" rows in their spreadsheet.

## Requirements

### Requirement: Monthly entry per concept
The system SHALL track, for each concept and each year/month, a `monto_planeado` (planned amount), an optional `monto_pagado` (actual amount paid, nullable until paid), a `pagado` status, and a `fecha_pago` (the date the entry was marked paid, nullable until paid). The system SHALL record today's date as `fecha_pago` the moment an entry transitions to `pagado`, and SHALL clear `fecha_pago` if the entry is later marked unpaid.

#### Scenario: Record a planned amount
- **WHEN** a user sets the planned amount for a concept in a given year/month
- **THEN** the system saves that `monto_planeado` for that concept/year/month

#### Scenario: Record a payment that differs from the plan
- **WHEN** a user marks a monthly entry as paid with a `monto_pagado` different from its `monto_planeado`
- **THEN** the system saves both values independently and marks the entry `pagado`

#### Scenario: Only one entry per concept per month
- **WHEN** a monthly entry already exists for a given concept, year, and month
- **THEN** the system updates that existing entry instead of creating a duplicate

#### Scenario: Marking an entry paid records the payment date
- **WHEN** a user marks a monthly entry as paid
- **THEN** the system records today's date as that entry's `fecha_pago`

#### Scenario: Marking an already-paid entry paid again does not change the date
- **WHEN** a user updates an entry that is already `pagado` without changing its paid status
- **THEN** the system leaves the existing `fecha_pago` unchanged

#### Scenario: Marking an entry unpaid clears the payment date
- **WHEN** a user marks a previously paid entry as unpaid
- **THEN** the system clears that entry's `fecha_pago`

### Requirement: Auto-generate future monthly entries
The system SHALL automatically create monthly entries for the remaining months of the current calendar year, using the most recently used planned amount, when a recurring concept (`deuda`, `gasto_fijo`, or `ingreso` that is active) is created or its planned amount is edited, unless that concept has a fixed `duracion_meses` set (see the fixed-duration requirement) or is a debt with amortization data (see the amortization-schedule requirement).

#### Scenario: Creating a recurring concept generates the rest of the year
- **WHEN** a user creates an active `gasto_fijo` concept with a planned monthly amount in month M of the current year
- **THEN** the system creates monthly entries with that planned amount for months M through December of the current year

#### Scenario: Creating a recurring income generates the rest of the year
- **WHEN** a user creates an active `ingreso` concept with a planned monthly amount in month M of the current year
- **THEN** the system creates monthly entries with that planned amount for months M through December of the current year, the same as it already does for `gasto_fijo`

#### Scenario: Editing a planned amount updates future months
- **WHEN** a user changes the planned amount for a concept's current month
- **THEN** the system applies that new planned amount to that month's entry and to the auto-generated entries for the remaining future months, without altering already-recorded past months

#### Scenario: Finished concepts are not auto-generated
- **WHEN** a concept has been marked finished
- **THEN** the system does not generate further monthly entries for it

### Requirement: Monthly net balance summary
The system SHALL provide, for a given user/year/month, a summary that computes `balance_neto` as the sum, across that user's active `ingreso` concepts for that month, of each entry's `monto_pagado` when paid or `monto_planeado` when not yet paid, plus the sum of `interes` across that user's abonos whose `fecha` falls in that month, minus the same paid-or-planned sum across that user's active `deuda` and `gasto_fijo` concepts for that month, minus the sum of that user's `Gasto.monto` whose `fecha` falls in that month.

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

### Requirement: Auto-generation uses the amortization schedule for amortized debts
The system SHALL, for a debt concept with amortization data, generate monthly entries for its amortization schedule from its starting installment (installment 1 by default, or `cuota_inicial` when set) through `numero_cuotas` (one entry per installment, spanning beyond the current calendar year if needed) at creation time, using each installment's fixed amount from the schedule instead of the copy-last-amount-forward behavior used for other recurring concepts.

#### Scenario: Multi-year debt generates entries beyond the current year
- **WHEN** a debt is created with `numero_cuotas` greater than the number of months remaining in the current calendar year
- **THEN** the system generates monthly entries continuing into the following year(s) until all installments have an entry, not just through December of the current year

#### Scenario: Generated amounts follow the schedule, not a flat copy
- **WHEN** an amortized debt's fixed installment is computed
- **THEN** every auto-generated entry for that debt uses that fixed installment amount as `monto_planeado`, consistent across all its months

#### Scenario: Non-amortized recurring concepts are unaffected
- **WHEN** a `deuda` concept without amortization data, or a `gasto_fijo` concept, is created or edited
- **THEN** auto-generation continues to behave exactly as before this change (copy-last-amount-forward through December of the current year)

#### Scenario: Generation starts at the debt's starting installment
- **WHEN** an amortized debt has `cuota_inicial` set to a value greater than 1
- **THEN** the system generates entries beginning at that installment rather than installment 1, with the first generated entry landing in the concept's creation month

### Requirement: Fixed-duration recurring concepts generate their whole window at creation
The system SHALL, for a `gasto_fijo` or `ingreso` concept created with both a `duracion_meses` and an initial planned amount, generate monthly entries for exactly `duracion_meses` consecutive months starting at the creation month (spanning into future years if needed), using that planned amount for every one of those months, and SHALL NOT generate further entries for that concept beyond that window.

#### Scenario: Fixed-duration income generates exactly its window
- **WHEN** a user creates an `ingreso` concept with a planned amount and `duracion_meses` of 6
- **THEN** the system generates exactly 6 consecutive monthly entries starting at the creation month, using that planned amount for each

#### Scenario: No further auto-generation beyond the fixed window
- **WHEN** the user later edits the planned amount of a month within a fixed-duration concept's already-generated window
- **THEN** the system does not generate any additional months beyond the original window

#### Scenario: Fixed duration can span into a future year
- **WHEN** a fixed-duration concept is created with `duracion_meses` greater than the number of months remaining in the current calendar year
- **THEN** the generated entries continue into the following year until the full duration is covered, consistent with how amortized debts already span years

### Requirement: Monthly entries report whether they are overdue
The system SHALL compute, for each monthly entry belonging to a concept with `dia_vencimiento` set, an `vencida` flag that is true when the entry is not `pagado` and the date formed by combining the entry's `anio`/`mes` with the concept's `dia_vencimiento` is before the current date. For entries belonging to a concept without `dia_vencimiento` set, `vencida` SHALL be false.

#### Scenario: Unpaid entry past its due date is overdue
- **WHEN** a monthly entry's concept has `dia_vencimiento` set, the entry is not `pagado`, and its computed due date has already passed
- **THEN** the system reports that entry's `vencida` as true

#### Scenario: Paid entry is never overdue
- **WHEN** a monthly entry is `pagado`, regardless of its computed due date
- **THEN** the system reports that entry's `vencida` as false

#### Scenario: Entry not yet due is not overdue
- **WHEN** a monthly entry's computed due date has not yet passed
- **THEN** the system reports that entry's `vencida` as false

#### Scenario: Entries without a due day configured are never flagged
- **WHEN** a monthly entry's concept has no `dia_vencimiento` set
- **THEN** the system reports that entry's `vencida` as false, regardless of payment status

### Requirement: Indefinite recurring concepts auto-extend into a new year on demand
The system SHALL, when listing an active, indefinite recurring concept's monthly entries (no `duracion_meses`, no amortization data) and no entry exists for the real current year and month, generate entries from the current month through December of the current year using the planned amount from that concept's most recently dated existing entry, without overwriting any existing entry. If the concept has no existing entry at all, the system SHALL NOT generate anything, since there is no known planned amount to carry forward.

#### Scenario: Visiting a concept in a new year fills the gap
- **WHEN** a user views an indefinite recurring concept's entries and the real current month has no entry, while at least one earlier entry exists
- **THEN** the system generates entries from the current month through December of the current year using the most recent existing entry's planned amount, before returning the list

#### Scenario: Existing entries are never overwritten
- **WHEN** the system generates entries to fill a new year's gap
- **THEN** any month that already has an entry, in that year or otherwise, is left unchanged

#### Scenario: No prior entry means no generation
- **WHEN** an indefinite recurring concept has no existing monthly entries at all
- **THEN** the system does not generate any entries when its entry list is viewed, leaving the gap for the user to fill manually

#### Scenario: Fixed-window concepts are unaffected
- **WHEN** a concept has `duracion_meses` set or has amortization data
- **THEN** viewing its entries never triggers this year-extension behavior, consistent with those concepts' fixed, already-fully-generated window

#### Scenario: A concept whose latest entry is in the future is not backfilled
- **WHEN** an indefinite recurring concept's most recently dated entry is for a month after the real current month
- **THEN** the system does not generate anything, since there is no past gap to catch up from

### Requirement: A monthly entry can be individually deleted
The system SHALL allow a user to delete a single monthly entry of a concept, restoring that month to having no entry at all. This SHALL only be allowed for concepts without a fixed window (no `duracion_meses`, no amortization data) - deletion SHALL be rejected for a concept with amortization data or `duracion_meses` set, since removing one installment from a generated schedule would leave an incoherent gap in it.

#### Scenario: Delete a mistakenly added entry
- **WHEN** a user deletes a monthly entry belonging to an indefinite recurring concept
- **THEN** the system removes that entry, and the month subsequently reports as having no entry

#### Scenario: Reject deletion on a fixed-window concept
- **WHEN** a user attempts to delete a monthly entry belonging to a concept with amortization data or `duracion_meses` set
- **THEN** the system rejects the request without deleting the entry

#### Scenario: Deleting a non-existent entry
- **WHEN** a user attempts to delete a monthly entry for a year/month that has no entry
- **THEN** the system rejects the request with a not-found error

#### Scenario: A deleted entry is not specially protected from re-generation
- **WHEN** the deleted entry was for the real current month of an indefinite recurring concept, and an earlier entry exists to copy an amount from
- **THEN** the system's existing year-extension behavior may regenerate that month's entry the next time the concept's entries are listed, unchanged from that behavior's normal rules
