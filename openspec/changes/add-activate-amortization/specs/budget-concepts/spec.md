## ADDED Requirements

### Requirement: Add amortization terms to an existing debt
The system SHALL allow a user to set `valor_total`, `tasa_interes`, `periodo_tasa`, `numero_cuotas`, and optionally `cuota_inicial` on a debt concept that does not yet have amortization data, via a dedicated activation request distinct from the plain concept-update path (which does not accept these fields). Any of that concept's not-yet-paid monthly entries SHALL be replaced by a newly generated schedule anchored to today; entries already marked paid SHALL be left unchanged as historical record. The system SHALL reject this request on a concept that already has amortization data, and on a concept whose type is not `deuda`.

#### Scenario: Activating amortization on a plain debt generates its schedule
- **WHEN** a user activates amortization on a debt concept with no existing amortization data, providing `valor_total`, `tasa_interes`, `periodo_tasa`, and `numero_cuotas`
- **THEN** the system computes a fixed installment amount and generates a schedule of monthly entries anchored to today

#### Scenario: Already-paid entries are preserved as history
- **WHEN** a user activates amortization on a debt concept that has one or more monthly entries already marked paid
- **THEN** those paid entries are left completely unchanged

#### Scenario: Not-yet-paid entries are replaced
- **WHEN** a user activates amortization on a debt concept that has not-yet-paid monthly entries
- **THEN** those entries are deleted and replaced by the newly generated schedule

#### Scenario: Starting partway through with cuota_inicial
- **WHEN** a user activates amortization providing a `cuota_inicial` greater than 1
- **THEN** the generated schedule starts at that installment number, matching how `cuota_inicial` already works at creation time

#### Scenario: Activation is rejected on an already-amortized debt
- **WHEN** a user attempts to activate amortization on a debt concept that already has `tasa_interes` and `numero_cuotas` set
- **THEN** the system rejects the request without changing the concept or its entries

#### Scenario: Activation is rejected on non-debt concepts
- **WHEN** a user attempts to activate amortization on a concept whose type is not `deuda`
- **THEN** the system rejects the request
