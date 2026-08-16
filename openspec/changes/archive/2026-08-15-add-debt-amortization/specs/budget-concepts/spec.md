## ADDED Requirements

### Requirement: Debt concepts can define amortization terms
The system SHALL allow a concept of type `deuda` to optionally specify `tasa_interes` (a numeric interest rate), `periodo_tasa` (`mensual` or `anual`, indicating how `tasa_interes` is expressed), and `numero_cuotas` (total installment count). The system SHALL require `tasa_interes` and `numero_cuotas` together: providing one without the other SHALL be rejected. These fields SHALL be rejected on concepts of type `gasto_fijo` or `ingreso`.

#### Scenario: Create a debt with full amortization terms
- **WHEN** a user creates a `deuda` concept with `valor_total`, `tasa_interes`, `periodo_tasa`, and `numero_cuotas` all provided
- **THEN** the system saves the concept with its amortization terms

#### Scenario: Reject interest rate without installment count
- **WHEN** a user attempts to create a `deuda` concept with `tasa_interes` but no `numero_cuotas`
- **THEN** the system rejects the request

#### Scenario: Reject installment count without interest rate
- **WHEN** a user attempts to create a `deuda` concept with `numero_cuotas` but no `tasa_interes`
- **THEN** the system rejects the request

#### Scenario: Amortization terms remain optional
- **WHEN** a user creates a `deuda` concept with only `valor_total` and no amortization fields
- **THEN** the system saves the concept exactly as before this change, with no amortization schedule

### Requirement: Fixed installment computed for amortized debts
The system SHALL, when a debt concept has both `tasa_interes` and `numero_cuotas`, compute a fixed monthly installment amount using the standard fixed-installment (French) amortization method, converting `tasa_interes` to a monthly rate first when `periodo_tasa` is `anual`, and SHALL generate the full installment-by-installment amortization schedule (interest portion, principal portion, and resulting balance per installment).

#### Scenario: Annual rate is converted before calculating the installment
- **WHEN** a debt is created with `periodo_tasa` set to `anual`
- **THEN** the system converts the annual rate to its equivalent monthly rate before computing the fixed installment, rather than treating the annual number as if it were monthly

#### Scenario: Schedule reflects declining balance
- **WHEN** the amortization schedule is generated for a debt
- **THEN** each successive installment's interest portion is computed against the declining balance from the prior installment, and the final installment's ending balance is zero

### Requirement: Financial terms are immutable once amortization data exists
The system SHALL reject changes to `valor_total`, `tasa_interes`, `periodo_tasa`, and `numero_cuotas` on any debt concept that has amortization data set. Changing these terms requires deleting the concept and creating a new one.

#### Scenario: Reject editing the amount of an amortized debt
- **WHEN** a user attempts to update `valor_total` on a debt concept that has `tasa_interes` and `numero_cuotas` set
- **THEN** the system rejects the request without changing the concept

#### Scenario: Non-amortized debts remain editable as before
- **WHEN** a user updates `valor_total` on a debt concept that has no amortization data
- **THEN** the system accepts the change, unchanged from prior behavior
