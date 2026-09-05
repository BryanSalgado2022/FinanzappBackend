## MODIFIED Requirements

### Requirement: Remaining balance reflects recorded payments
The system SHALL compute a debtor's remaining balance as `monto_total` minus the sum, across all of its recorded abonos, of each abono's principal portion (`monto` minus `interes`, where `interes` defaults to zero when not set), and SHALL NOT store this figure. For an amortized debtor (one with `tasa_interes` and `numero_cuotas` set), the system SHALL instead compute remaining balance as its effective starting amount minus the sum of `monto_pagado` across all of its scheduled installments, and SHALL NOT use its abonos for this computation.

#### Scenario: Remaining balance decreases as abonos are recorded
- **WHEN** a debtor has one or more abonos recorded against it, none with an `interes` value
- **THEN** the reported remaining balance is `monto_total` minus the sum of those abono amounts

#### Scenario: Remaining balance with no abonos equals the full amount
- **WHEN** a debtor has no abonos recorded
- **THEN** the reported remaining balance equals its `monto_total`

#### Scenario: Interest portion of an abono does not reduce the remaining balance
- **WHEN** an abono is recorded with an `interes` value less than its `monto`
- **THEN** the remaining balance decreases only by `monto - interes`, not by the full `monto`

#### Scenario: Remaining balance for an amortized debtor reflects paid installments
- **WHEN** an amortized debtor has one or more of its scheduled installments marked paid
- **THEN** the reported remaining balance is its effective starting amount minus the sum of `monto_pagado` across those paid installments, regardless of any abonos that may exist

#### Scenario: Remaining balance for an amortized debtor with no installments paid equals the full amount
- **WHEN** an amortized debtor has no installment marked paid yet
- **THEN** the reported remaining balance equals its effective starting amount

### Requirement: Record a partial payment (abono)
The system SHALL allow a user to record an abono (partial payment) against a debtor they own, with a required `monto` and `fecha`, and an optional `interes` representing how much of `monto` was interest rather than principal. `interes`, when provided, SHALL NOT exceed `monto`. The system SHALL reject recording an abono against an amortized debtor (one with `tasa_interes` and `numero_cuotas` set) — an amortized debtor tracks payments through its installment schedule instead.

#### Scenario: Recording an abono
- **WHEN** a user records an abono with a `monto` and `fecha` against one of their debtors
- **THEN** the system saves the abono and the debtor's reported remaining balance reflects it

#### Scenario: Recording an abono against another user's debtor
- **WHEN** a user attempts to record an abono against a debtor id that belongs to a different user
- **THEN** the system responds as if the debtor does not exist and does not record the abono

#### Scenario: Recording an abono with an interest portion
- **WHEN** a user records an abono with both `monto` and an `interes` value less than or equal to `monto`
- **THEN** the system saves both values on the abono

#### Scenario: Interest cannot exceed the abono amount
- **WHEN** a user attempts to record an abono with `interes` greater than `monto`
- **THEN** the system rejects the request and does not record the abono

#### Scenario: Abono creation rejected for an amortized debtor
- **WHEN** a user attempts to record an abono against a debtor that has `tasa_interes` and `numero_cuotas` set
- **THEN** the system rejects the request and does not record the abono

## ADDED Requirements

### Requirement: Create an amortized debtor
The system SHALL allow a user to optionally set `tasa_interes`, `periodo_tasa`, and `numero_cuotas` together when creating a debtor, defaulting `periodo_tasa` to monthly when omitted, and SHALL reject `tasa_interes` or `numero_cuotas` being provided without the other. The system SHALL allow an optional `cuota_inicial` only when both of those are set, rejecting a value greater than `numero_cuotas`. When amortization terms are set, the system SHALL compute a fixed installment amount and generate the debtor's full installment schedule anchored to its own `fecha`, starting from `cuota_inicial` (defaulting to the first installment) through `numero_cuotas`.

#### Scenario: Creating an amortized debtor generates its schedule
- **WHEN** a user creates a debtor with `tasa_interes`, `periodo_tasa`, and `numero_cuotas`
- **THEN** the system computes a fixed installment amount and generates one scheduled installment per period from the debtor's `fecha` through `numero_cuotas`

#### Scenario: tasa_interes and numero_cuotas must be provided together
- **WHEN** a user attempts to create a debtor with only one of `tasa_interes` or `numero_cuotas` set
- **THEN** the system rejects the request

#### Scenario: cuota_inicial requires amortization terms
- **WHEN** a user attempts to create a debtor with `cuota_inicial` but without both `tasa_interes` and `numero_cuotas`
- **THEN** the system rejects the request

#### Scenario: cuota_inicial cannot exceed numero_cuotas
- **WHEN** a user attempts to create a debtor with `cuota_inicial` greater than `numero_cuotas`
- **THEN** the system rejects the request

#### Scenario: A debtor with no amortization terms behaves exactly as before
- **WHEN** a user creates a debtor without `tasa_interes` or `numero_cuotas`
- **THEN** no installment schedule is generated and the debtor behaves exactly as debtors did before this capability existed

### Requirement: View and pay a debtor's scheduled installments
The system SHALL allow a user to list the scheduled installments of one of their debtors, and to record the actual amount paid and mark an individual installment paid or unpaid. The system SHALL record the date an installment transitions to paid, and SHALL clear that date if it is marked unpaid again. Installments SHALL NOT be individually deleted or created outside of the generated schedule.

#### Scenario: Listing a debtor's scheduled installments
- **WHEN** a user requests the list of scheduled installments for one of their amortized debtors
- **THEN** the system returns every installment in that debtor's generated schedule

#### Scenario: Marking an installment paid records the amount and date
- **WHEN** a user marks a scheduled installment paid, optionally with an actual amount paid
- **THEN** the system saves the actual amount (defaulting to the planned amount when not given) and records today's date as its payment date

#### Scenario: Marking an installment unpaid clears its payment date
- **WHEN** a user marks a previously paid installment unpaid again
- **THEN** the system clears its recorded payment date

#### Scenario: Listing installments for another user's debtor
- **WHEN** a user attempts to list installments for a debtor id that belongs to a different user
- **THEN** the system responds as if the debtor does not exist

### Requirement: Correct an amortized debtor's terms
The system SHALL allow a user to correct an amortized debtor's `monto_total`, `tasa_interes`, `periodo_tasa`, and `numero_cuotas` together after creation. Installments already marked paid SHALL be left unchanged; every not-yet-paid installment SHALL be replaced by a newly generated schedule continuing from the month after the last paid installment (or from today, if none are paid). The system SHALL reject a `numero_cuotas` value lower than the number of installments already paid. `cuota_inicial` SHALL remain unchanged by this correction and cannot be set through it.

#### Scenario: Correcting terms replaces only unpaid installments
- **WHEN** a user corrects the terms of an amortized debtor that has one or more installments already paid
- **THEN** the paid installments are left unchanged and every unpaid installment is replaced by a schedule regenerated from the new terms, continuing the month after the last paid installment

#### Scenario: Correcting terms with no installments paid regenerates from today
- **WHEN** a user corrects the terms of an amortized debtor with no installments paid yet
- **THEN** the system deletes its existing schedule and generates a new one starting today

#### Scenario: Reducing numero_cuotas below installments already paid is rejected
- **WHEN** a user attempts to set `numero_cuotas` lower than the number of installments already marked paid
- **THEN** the system rejects the request and makes no changes

#### Scenario: Correcting terms on a non-amortized debtor is rejected
- **WHEN** a user attempts to correct amortization terms on a debtor that has no existing `tasa_interes`/`numero_cuotas`
- **THEN** the system rejects the request
