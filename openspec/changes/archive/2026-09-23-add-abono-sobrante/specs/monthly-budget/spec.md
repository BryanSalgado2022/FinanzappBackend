## ADDED Requirements

### Requirement: Route a payment surplus into a principal prepayment
The system SHALL allow a user marking a monthly entry paid to optionally specify how a surplus (an actual amount paid greater than the entry's planned amount) should be applied to the remaining schedule of an amortized debt, using the same `reducir_plazo`/`reducir_cuota` choice as a standalone principal prepayment. When this choice is given, the system SHALL record only the planned amount against that entry and route the surplus into a principal prepayment, in the same request. The system SHALL reject this when there is no surplus to route, or when the concept is not an amortized debt.

#### Scenario: A surplus is routed into a principal prepayment
- **WHEN** a user marks a debt's monthly entry paid with an actual amount greater than its planned amount, and specifies `reducir_plazo` or `reducir_cuota`
- **THEN** the entry's recorded amount equals its planned amount, and the surplus is recorded as a principal prepayment applied per the chosen mode

#### Scenario: Marking an entry paid without a mode is unchanged
- **WHEN** a user marks an entry paid with any actual amount and does not specify a mode
- **THEN** the system records the actual amount as given, exactly as before this change

#### Scenario: Rejected when there is no surplus
- **WHEN** a user specifies a mode but the actual amount paid does not exceed the entry's planned amount
- **THEN** the system rejects the request

#### Scenario: Rejected on a non-amortized debt
- **WHEN** a user specifies a mode while marking paid an entry belonging to a concept that is not an amortized debt
- **THEN** the system rejects the request
