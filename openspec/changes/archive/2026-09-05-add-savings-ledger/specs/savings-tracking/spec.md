## Purpose
Lets a user record dated savings contributions and withdrawals over time, see the resulting running balance and full history, and correct mistaken entries — replacing a single overwritable figure with a growing, auditable record of how their savings actually changed.

## ADDED Requirements

### Requirement: Record a savings contribution or withdrawal
The system SHALL allow an authenticated user to record a savings ledger entry with a required `monto` (always a positive amount), a required `fecha`, and a required `tipo` of either `aporte` (contribution) or `retiro` (withdrawal).

#### Scenario: Recording a contribution
- **WHEN** a user records an entry with `tipo=aporte`, a `monto`, and a `fecha`
- **THEN** the system saves it and the user's running savings balance increases by that `monto`

#### Scenario: Recording a withdrawal
- **WHEN** a user records an entry with `tipo=retiro`, a `monto`, and a `fecha`
- **THEN** the system saves it and the user's running savings balance decreases by that `monto`

### Requirement: Withdrawals have no effect on any other balance calculation
The system SHALL NOT let a recorded `retiro` (or `aporte`) affect the monthly summary, `balance_neto`, or any other computed figure outside of the user's own savings running balance. Recording a withdrawal is purely informational bookkeeping about money the user says they took out of savings, never an input to any other calculation.

#### Scenario: A withdrawal does not change the monthly summary
- **WHEN** a user records a `retiro` with a `fecha` in a given month
- **THEN** that month's summary (`total_ingresos`, `total_gastos`, `balance_neto`) is completely unaffected by it

#### Scenario: A contribution does not change the monthly summary
- **WHEN** a user records an `aporte` with a `fecha` in a given month
- **THEN** that month's summary is completely unaffected by it

### Requirement: View savings history and running balance
The system SHALL allow a user to list all of their recorded savings ledger entries, and SHALL compute their running savings balance as the sum of all `aporte` amounts minus the sum of all `retiro` amounts, defaulting to zero when they have no entries.

#### Scenario: Listing savings entries
- **WHEN** a user requests their savings ledger
- **THEN** the system returns only entries owned by that user

#### Scenario: Running balance reflects a mix of contributions and withdrawals
- **WHEN** a user has recorded both `aporte` and `retiro` entries
- **THEN** their running balance equals the sum of all `aporte` amounts minus the sum of all `retiro` amounts

#### Scenario: Running balance with no entries is zero
- **WHEN** a user has no savings ledger entries recorded
- **THEN** their running balance is reported as zero, not absent or an error

### Requirement: Delete a savings ledger entry
The system SHALL allow a user to delete one of their own savings ledger entries, which SHALL update their running balance accordingly.

#### Scenario: Deleting an entry updates the balance
- **WHEN** a user deletes a previously recorded ledger entry
- **THEN** the entry no longer appears in their history and their running balance reflects its removal

#### Scenario: Deleting another user's entry is rejected
- **WHEN** a user attempts to delete a savings ledger entry id that belongs to a different user
- **THEN** the system responds as if the entry does not exist and does not delete it
