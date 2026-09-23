## ADDED Requirements

### Requirement: Route a payment surplus into a principal prepayment
The system SHALL allow a user marking a debtor's installment paid to optionally specify how a surplus (an actual amount paid greater than the installment's planned amount) should be applied to the remaining schedule, using the same `reducir_plazo`/`reducir_cuota` choice as a standalone principal prepayment. When this choice is given, the system SHALL record only the planned amount against that installment and route the surplus into a principal prepayment, in the same request. The system SHALL reject this when there is no surplus to route, or when the debtor is not amortized.

#### Scenario: A surplus is routed into a principal prepayment
- **WHEN** a user marks an installment paid with an actual amount greater than its planned amount, and specifies `reducir_plazo` or `reducir_cuota`
- **THEN** the installment's recorded amount equals its planned amount, and the surplus is recorded as a principal prepayment applied per the chosen mode

#### Scenario: Marking an installment paid without a mode is unchanged
- **WHEN** a user marks an installment paid with any actual amount and does not specify a mode
- **THEN** the system records the actual amount as given, exactly as before this change

#### Scenario: Rejected when there is no surplus
- **WHEN** a user specifies a mode but the actual amount paid does not exceed the installment's planned amount
- **THEN** the system rejects the request

#### Scenario: Rejected on a non-amortized debtor
- **WHEN** a user specifies a mode while marking paid an installment belonging to a debtor that is not amortized
- **THEN** the system rejects the request
