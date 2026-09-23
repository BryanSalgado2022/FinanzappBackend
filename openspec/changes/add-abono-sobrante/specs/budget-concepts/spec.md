## ADDED Requirements

### Requirement: Record a principal prepayment on an amortized debt
The system SHALL allow a user to record an extraordinary principal prepayment against an amortized debt concept, with a required `monto` and `fecha`, and a required choice of how the reduction is applied to the remaining schedule: `reducir_plazo` (keep the fixed installment amount, reduce the remaining number of installments) or `reducir_cuota` (keep the remaining number of installments, reduce the fixed installment amount). The system SHALL reject this on a debt that is not amortized.

#### Scenario: Recording a prepayment with reducir_plazo
- **WHEN** a user records a principal prepayment with `modo=reducir_plazo` against an amortized debt
- **THEN** the debt's remaining balance decreases by the prepayment amount, its fixed installment amount stays the same (aside from rounding), and its remaining schedule shortens

#### Scenario: Recording a prepayment with reducir_cuota
- **WHEN** a user records a principal prepayment with `modo=reducir_cuota` against an amortized debt
- **THEN** the debt's remaining balance decreases by the prepayment amount, its remaining number of installments stays the same, and its fixed installment amount decreases

#### Scenario: Already-paid entries are untouched
- **WHEN** a user records a principal prepayment against a debt that has one or more entries already paid
- **THEN** those entries remain unchanged

#### Scenario: Prepayment rejected on a non-amortized debt
- **WHEN** a user attempts to record a principal prepayment against a debt concept with no `tasa_interes`/`numero_cuotas` set
- **THEN** the system rejects the request

#### Scenario: reducir_plazo rejected when the installment no longer covers interest
- **WHEN** a user records a principal prepayment with `modo=reducir_plazo` whose fixed installment amount would no longer cover the interest on the reduced balance
- **THEN** the system rejects the request and does not record the prepayment

### Requirement: A prepayment that fully settles the balance closes the debt
The system SHALL, when a principal prepayment reduces an amortized debt's remaining balance to zero, mark the concept finished — the same transition as manually marking it finished, including recording today's date.

#### Scenario: Full prepayment closes the debt
- **WHEN** a user records a principal prepayment for an amount equal to or greater than an amortized debt's remaining balance
- **THEN** the concept is marked finished, with today's date recorded, and its remaining not-yet-paid entries are removed

### Requirement: Fixed installment amount reflects the current schedule
The system SHALL report an amortized debt's fixed installment amount as the planned amount of its next not-yet-paid entry, so it stays accurate after a principal prepayment changes the remaining schedule without altering the concept's originally recorded terms.

#### Scenario: Fixed installment updates after a prepayment
- **WHEN** a user views an amortized debt's detail after recording a principal prepayment
- **THEN** the reported fixed installment amount matches the newly generated schedule, not the original terms recorded at creation
