## MODIFIED Requirements

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

## ADDED Requirements

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
