## MODIFIED Requirements

### Requirement: Debt and fixed-expense concepts can define a due day
The system SHALL allow a concept of any type (`deuda`, `gasto_fijo`, or `ingreso`) to optionally specify `dia_vencimiento`, an integer day-of-month between 1 and 28. `dia_vencimiento` SHALL be settable at creation and editable at any time thereafter — it is not subject to the immutability rule that applies to amortization terms, since changing it does not require recalculating any schedule.

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
- **WHEN** a user creates or updates an `ingreso` concept with `dia_vencimiento` set to a value between 1 and 28
- **THEN** the system saves that value on the concept, since `dia_vencimiento` validation no longer treats `ingreso` differently from `deuda` or `gasto_fijo`

#### Scenario: Due day remains editable after creation
- **WHEN** a user updates `dia_vencimiento` on an existing concept, including one with amortization data set
- **THEN** the system accepts the change, independent of whether the concept's financial terms are otherwise locked

#### Scenario: Due day remains optional
- **WHEN** a user creates a concept without `dia_vencimiento`
- **THEN** the system saves the concept exactly as before this change, with no due day set

### Requirement: Update and finish a concept
The system SHALL allow a user to update a concept's name, category assignments, or status, and SHALL allow marking a concept as finished so it stops being treated as an active recurring item. The system SHALL record the date a concept was marked finished, and SHALL clear that date if the concept is reactivated.

#### Scenario: Mark a debt as finished
- **WHEN** a user marks a fully paid debt concept as finished
- **THEN** the system stops including that concept when auto-generating future monthly entries, while preserving its historical entries

#### Scenario: Replace a concept's category assignments
- **WHEN** a user updates a concept with a new list of category ids
- **THEN** the system replaces the concept's prior category assignments with exactly the categories in the new list

#### Scenario: Concept persists across years by default
- **WHEN** a calendar year ends and an active concept has not been marked finished or deleted
- **THEN** the concept remains active and available for the new year without the user recreating it

#### Scenario: Finishing a concept records the date
- **WHEN** a user marks an active concept `activo: false`
- **THEN** the system records today's date as the concept's finished date

#### Scenario: Reactivating a concept clears the finished date
- **WHEN** a user marks a previously finished concept `activo: true` again
- **THEN** the system clears its recorded finished date
