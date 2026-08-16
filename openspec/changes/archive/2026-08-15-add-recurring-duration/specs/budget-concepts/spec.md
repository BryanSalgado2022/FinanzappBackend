## ADDED Requirements

### Requirement: Fixed-duration recurring concepts
The system SHALL allow a concept of type `gasto_fijo` or `ingreso` to optionally specify `duracion_meses` (a number of months), and SHALL reject `duracion_meses` on concepts of type `deuda`.

#### Scenario: Create a fixed-duration income
- **WHEN** a user creates an `ingreso` concept with `duracion_meses` set
- **THEN** the system saves the concept with that duration

#### Scenario: Duration remains optional
- **WHEN** a user creates a `gasto_fijo` or `ingreso` concept without `duracion_meses`
- **THEN** the system saves the concept exactly as before this change, with indefinite/open-ended recurrence

#### Scenario: Reject duration on a debt
- **WHEN** a user attempts to set `duracion_meses` on a `deuda` concept
- **THEN** the system rejects the request
