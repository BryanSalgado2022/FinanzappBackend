## MODIFIED Requirements

### Requirement: Debt remaining balance
The system SHALL compute a debt concept's remaining balance as its effective starting amount minus the sum of `monto_pagado` across every monthly entry ever recorded for that concept, regardless of year, and SHALL NOT reset this balance when the calendar year changes. For a debt with amortization data and no starting installment set (or a starting installment of 1), the effective starting amount is `valor_total`. For a debt with amortization data and a starting installment greater than 1, the effective starting amount is the schedule's balance immediately after the installment preceding the starting one, since no entries or payments exist in the system for the skipped installments.

#### Scenario: Remaining balance reflects payments across years
- **WHEN** a debt concept has payments recorded in more than one calendar year
- **THEN** the system's reported remaining balance subtracts all of those payments from its effective starting amount, not just the current year's

#### Scenario: Debt fully paid off
- **WHEN** the sum of a debt concept's recorded payments reaches its effective starting amount
- **THEN** the system reports a remaining balance of zero (not negative, if payments exactly match)

#### Scenario: Remaining balance for a debt with a starting installment
- **WHEN** an amortized debt has a starting installment greater than 1
- **THEN** the reported remaining balance is computed from the schedule's balance at that starting point, not from the full original `valor_total`

### Requirement: Financial terms are immutable once amortization data exists
The system SHALL reject changes to `valor_total`, `tasa_interes`, `periodo_tasa`, `numero_cuotas`, and `cuota_inicial` on any debt concept that has amortization data set, with a descriptive error explaining that the concept must be deleted and recreated to change these terms. Changing these terms requires deleting the concept and creating a new one.

#### Scenario: Reject editing the amount of an amortized debt
- **WHEN** a user attempts to update `valor_total` on a debt concept that has `tasa_interes` and `numero_cuotas` set
- **THEN** the system rejects the request without changing the concept

#### Scenario: Reject editing the starting installment
- **WHEN** a user attempts to update `cuota_inicial` on an existing debt concept
- **THEN** the system rejects the request with a message explaining that the concept must be deleted and recreated to change it, without changing the concept

#### Scenario: Non-amortized debts remain editable as before
- **WHEN** a user updates `valor_total` on a debt concept that has no amortization data
- **THEN** the system accepts the change, unchanged from prior behavior

## ADDED Requirements

### Requirement: Debt concepts can start partway through an existing amortization schedule
The system SHALL allow a debt concept with amortization data to optionally specify `cuota_inicial`, the installment number at which entry generation should begin, and SHALL reject `cuota_inicial` on a concept without amortization data or outside the range 1 to `numero_cuotas`. When set, only installments from `cuota_inicial` through `numero_cuotas` SHALL be generated as monthly entries; earlier installments are treated as already settled outside the system.

#### Scenario: Create a debt already partway through its schedule
- **WHEN** a user creates a `deuda` concept with amortization data and `cuota_inicial` set to a value greater than 1
- **THEN** the system generates monthly entries only for installments from `cuota_inicial` through `numero_cuotas`, starting at the concept's creation month

#### Scenario: Starting installment remains optional
- **WHEN** a user creates an amortized debt without specifying `cuota_inicial`
- **THEN** the system generates the full schedule starting at installment 1, exactly as before this change

#### Scenario: Reject a starting installment out of range
- **WHEN** a user attempts to set `cuota_inicial` to less than 1 or greater than `numero_cuotas`
- **THEN** the system rejects the request

#### Scenario: Reject a starting installment without amortization data
- **WHEN** a user attempts to set `cuota_inicial` on a concept that does not have both `tasa_interes` and `numero_cuotas`
- **THEN** the system rejects the request
