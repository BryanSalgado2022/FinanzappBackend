## Purpose

Lets each user track money other people owe them — the mirror image of the app's `deuda` concepts — recording who they lent to, how much, since when, and any collateral, with support for logging partial repayments over time so they don't lose track of what's still outstanding.

## ADDED Requirements

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
The system SHALL compute a debtor's remaining balance as `monto_total` minus the sum of all of its recorded abono amounts, and SHALL NOT store this figure.

#### Scenario: Remaining balance decreases as abonos are recorded
- **WHEN** a debtor has one or more abonos recorded against it
- **THEN** the reported remaining balance is `monto_total` minus the sum of those abono amounts

#### Scenario: Remaining balance with no abonos equals the full amount
- **WHEN** a debtor has no abonos recorded
- **THEN** the reported remaining balance equals its `monto_total`

### Requirement: Update and close a debtor
The system SHALL allow a user to update a debtor's `nombre`, `monto_total`, `fecha`, `garantia`, and `activo` status. Marking a debtor `activo: false` SHALL be allowed regardless of its remaining balance.

#### Scenario: Editing debtor details
- **WHEN** a user updates a debtor's `nombre`, `monto_total`, `fecha`, or `garantia`
- **THEN** the system saves the new values

#### Scenario: Closing a debtor that still has a balance
- **WHEN** a user marks a debtor `activo: false` while it still has a remaining balance greater than zero
- **THEN** the system accepts the change

### Requirement: Delete a debtor
The system SHALL allow a user to delete a debtor they own, which SHALL also remove all of its recorded abonos.

#### Scenario: Deleting a debtor removes its abonos
- **WHEN** a user deletes a debtor that has one or more abonos recorded
- **THEN** the debtor and all of its abonos are removed

### Requirement: Record a partial payment (abono)
The system SHALL allow a user to record an abono (partial payment) against a debtor they own, with a required `monto` and `fecha`.

#### Scenario: Recording an abono
- **WHEN** a user records an abono with a `monto` and `fecha` against one of their debtors
- **THEN** the system saves the abono and the debtor's reported remaining balance reflects it

#### Scenario: Recording an abono against another user's debtor
- **WHEN** a user attempts to record an abono against a debtor id that belongs to a different user
- **THEN** the system responds as if the debtor does not exist and does not record the abono

### Requirement: List and delete abonos
The system SHALL allow a user to list all abonos recorded against a debtor they own, and to delete an individual abono.

#### Scenario: Listing a debtor's abonos
- **WHEN** a user requests the list of abonos for one of their debtors
- **THEN** the system returns every abono recorded against that debtor

#### Scenario: Deleting an abono
- **WHEN** a user deletes one of their debtor's abonos
- **THEN** the abono is removed and the debtor's reported remaining balance reflects its removal
