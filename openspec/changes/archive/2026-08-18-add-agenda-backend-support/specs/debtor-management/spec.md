## MODIFIED Requirements

### Requirement: Update and close a debtor
The system SHALL allow a user to update a debtor's `nombre`, `monto_total`, `fecha`, `garantia`, and `activo` status. Marking a debtor `activo: false` SHALL be allowed regardless of its remaining balance. The system SHALL record the date a debtor was closed, and SHALL clear that date if the debtor is reactivated.

#### Scenario: Editing debtor details
- **WHEN** a user updates a debtor's `nombre`, `monto_total`, `fecha`, or `garantia`
- **THEN** the system saves the new values

#### Scenario: Closing a debtor that still has a balance
- **WHEN** a user marks a debtor `activo: false` while it still has a remaining balance greater than zero
- **THEN** the system accepts the change

#### Scenario: Closing a debtor records the date
- **WHEN** a user marks an active debtor `activo: false`
- **THEN** the system records today's date as the debtor's finished date

#### Scenario: Reactivating a debtor clears the finished date
- **WHEN** a user marks a previously closed debtor `activo: true` again
- **THEN** the system clears its recorded finished date
