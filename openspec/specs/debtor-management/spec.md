# debtor-management Specification

## Purpose
Lets each user track money other people owe them — the mirror image of the app's `deuda` concepts — recording who they lent to, how much, since when, and any collateral, with support for logging partial repayments over time so they don't lose track of what's still outstanding.

## Requirements

### Requirement: Create a debtor
The system SHALL allow an authenticated user to create a debtor record with a required `nombre`, `monto_total`, and `fecha`, and an optional `garantia`. A newly created debtor SHALL default to `activo: true`.

#### Scenario: Create a debtor with required fields only
- **WHEN** a user creates a debtor with `nombre`, `monto_total`, and `fecha`, and no `garantia`
- **THEN** the system saves the debtor as owned by that user, active, with no collateral recorded

#### Scenario: Create a debtor with collateral
- **WHEN** a user creates a debtor and supplies a `garantia` value
- **THEN** the system saves that value on the debtor

### Requirement: List and retrieve debtors
The system SHALL allow a user to list all of their debtors and retrieve a single debtor by id, including its computed remaining balance.

#### Scenario: List debtors
- **WHEN** a user requests their list of debtors
- **THEN** the system returns only debtors owned by that user

#### Scenario: Retrieve a debtor owned by another user
- **WHEN** a user attempts to retrieve a debtor id that belongs to a different user
- **THEN** the system responds as if the debtor does not exist

### Requirement: Remaining balance reflects recorded payments
The system SHALL compute a debtor's remaining balance as `monto_total` minus the sum, across all of its recorded abonos, of each abono's principal portion (`monto` minus `interes`, where `interes` defaults to zero when not set), and SHALL NOT store this figure.

#### Scenario: Remaining balance decreases as abonos are recorded
- **WHEN** a debtor has one or more abonos recorded against it, none with an `interes` value
- **THEN** the reported remaining balance is `monto_total` minus the sum of those abono amounts

#### Scenario: Remaining balance with no abonos equals the full amount
- **WHEN** a debtor has no abonos recorded
- **THEN** the reported remaining balance equals its `monto_total`

#### Scenario: Interest portion of an abono does not reduce the remaining balance
- **WHEN** an abono is recorded with an `interes` value less than its `monto`
- **THEN** the remaining balance decreases only by `monto - interes`, not by the full `monto`

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

### Requirement: Delete a debtor
The system SHALL allow a user to delete a debtor they own, which SHALL also remove all of its recorded abonos.

#### Scenario: Deleting a debtor removes its abonos
- **WHEN** a user deletes a debtor that has one or more abonos recorded
- **THEN** the debtor and all of its abonos are removed

### Requirement: Record a partial payment (abono)
The system SHALL allow a user to record an abono (partial payment) against a debtor they own, with a required `monto` and `fecha`, and an optional `interes` representing how much of `monto` was interest rather than principal. `interes`, when provided, SHALL NOT exceed `monto`.

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

### Requirement: List and delete abonos
The system SHALL allow a user to list all abonos recorded against a debtor they own, and to delete an individual abono.

#### Scenario: Listing a debtor's abonos
- **WHEN** a user requests the list of abonos for one of their debtors
- **THEN** the system returns every abono recorded against that debtor

#### Scenario: Deleting an abono
- **WHEN** a user deletes one of their debtor's abonos
- **THEN** the abono is removed and the debtor's reported remaining balance reflects its removal
