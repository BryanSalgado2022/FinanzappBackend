## MODIFIED Requirements

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
