## MODIFIED Requirements

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
