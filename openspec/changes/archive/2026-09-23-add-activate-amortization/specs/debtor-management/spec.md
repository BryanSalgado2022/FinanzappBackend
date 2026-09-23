## ADDED Requirements

### Requirement: Add amortization terms to an existing debtor
The system SHALL allow a user to set `monto_total`, `tasa_interes`, `periodo_tasa`, `numero_cuotas`, and optionally `cuota_inicial` on a debtor that does not yet have amortization data, via a dedicated activation request distinct from the plain debtor-update path. Any of that debtor's not-yet-paid scheduled installments SHALL be replaced by a newly generated schedule anchored to today; installments already marked paid SHALL be left unchanged as historical record. Existing abonos recorded before activation are left untouched as historical record and SHALL NOT be automatically reconciled against the new schedule. The system SHALL reject this request on a debtor that already has amortization data.

#### Scenario: Activating amortization on a plain debtor generates its schedule
- **WHEN** a user activates amortization on a debtor with no existing amortization data, providing `monto_total`, `tasa_interes`, `periodo_tasa`, and `numero_cuotas`
- **THEN** the system computes a fixed installment amount and generates a schedule of installments anchored to today

#### Scenario: Existing abonos are preserved as history
- **WHEN** a user activates amortization on a debtor that has abonos already recorded
- **THEN** those abonos remain visible as historical record and are not used to adjust the newly generated schedule

#### Scenario: Starting partway through with cuota_inicial
- **WHEN** a user activates amortization providing a `cuota_inicial` greater than 1
- **THEN** the generated schedule starts at that installment number, matching how `cuota_inicial` already works at creation time

#### Scenario: Activation is rejected on an already-amortized debtor
- **WHEN** a user attempts to activate amortization on a debtor that already has `tasa_interes` and `numero_cuotas` set
- **THEN** the system rejects the request without changing the debtor
