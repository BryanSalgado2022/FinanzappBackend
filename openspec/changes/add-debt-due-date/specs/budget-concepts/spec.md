## ADDED Requirements

### Requirement: Debt and fixed-expense concepts can define a due day
The system SHALL allow a concept of type `deuda` or `gasto_fijo` to optionally specify `dia_vencimiento`, an integer day-of-month between 1 and 28, and SHALL reject `dia_vencimiento` on concepts of type `ingreso`. `dia_vencimiento` SHALL be settable at creation and editable at any time thereafter — it is not subject to the immutability rule that applies to amortization terms, since changing it does not require recalculating any schedule.

#### Scenario: Set a due day on a debt
- **WHEN** a user creates or updates a `deuda` concept with `dia_vencimiento` set to a value between 1 and 28
- **THEN** the system saves that value on the concept

#### Scenario: Set a due day on a fixed expense
- **WHEN** a user creates or updates a `gasto_fijo` concept with `dia_vencimiento` set to a value between 1 and 28
- **THEN** the system saves that value on the concept

#### Scenario: Reject a due day outside the valid range
- **WHEN** a user attempts to set `dia_vencimiento` to a value less than 1 or greater than 28
- **THEN** the system rejects the request

#### Scenario: Reject a due day on an income concept
- **WHEN** a user attempts to set `dia_vencimiento` on a concept of type `ingreso`
- **THEN** the system rejects the request

#### Scenario: Due day remains editable after creation
- **WHEN** a user updates `dia_vencimiento` on an existing `deuda` or `gasto_fijo` concept, including one with amortization data set
- **THEN** the system accepts the change, independent of whether the concept's financial terms are otherwise locked

#### Scenario: Due day remains optional
- **WHEN** a user creates a `deuda` or `gasto_fijo` concept without `dia_vencimiento`
- **THEN** the system saves the concept exactly as before this change, with no due day set
