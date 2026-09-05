## MODIFIED Requirements

### Requirement: Financial terms are immutable once amortization data exists
The system SHALL reject changes to `cuota_inicial` on any debt concept, with a descriptive error explaining that the concept must be deleted and recreated to change it. The system SHALL reject changes to `valor_total`, `tasa_interes`, `periodo_tasa`, and `numero_cuotas` via the plain concept-update path on any debt concept that has amortization data set — these SHALL only be changeable via the dedicated amortization-recalculation path described in the "Amortized debts can have their financial terms corrected" requirement.

#### Scenario: Reject editing the amount of an amortized debt
- **WHEN** a user attempts to update `valor_total` via the plain concept-update endpoint on a debt concept that has `tasa_interes` and `numero_cuotas` set
- **THEN** the system rejects the request without changing the concept

#### Scenario: Reject editing the starting installment
- **WHEN** a user attempts to update `cuota_inicial` on an existing debt concept
- **THEN** the system rejects the request with a message explaining that the concept must be deleted and recreated to change it, without changing the concept

#### Scenario: Non-amortized debts remain editable as before
- **WHEN** a user updates `valor_total` on a debt concept that has no amortization data
- **THEN** the system accepts the change via the plain update path, unchanged from prior behavior

## ADDED Requirements

### Requirement: Amortized debts can have their financial terms corrected
The system SHALL let a user correct `valor_total`, `tasa_interes`, `periodo_tasa`, and `numero_cuotas` on a debt concept that already has amortization data, via a dedicated recalculation request providing all four values together. `cuota_inicial` is never part of this request and remains permanently unchangeable.

#### Scenario: Correcting a mistyped interest rate
- **WHEN** a user submits a recalculation request with a corrected `tasa_interes` and the same `valor_total`/`periodo_tasa`/`numero_cuotas` as before
- **THEN** the system accepts the change and updates the concept's stored terms

#### Scenario: Reducing installment count below what's already paid is rejected
- **WHEN** a user submits a recalculation request with a `numero_cuotas` smaller than the number of installments already marked paid on that concept
- **THEN** the system rejects the request without changing the concept or its entries

#### Scenario: Recalculation is only available on already-amortized debts
- **WHEN** a user attempts the recalculation request on a debt concept that has no amortization data at all
- **THEN** the system rejects the request, since there is no existing amortization to correct
