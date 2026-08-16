## ADDED Requirements

### Requirement: Auto-generation uses the amortization schedule for amortized debts
The system SHALL, for a debt concept with amortization data, generate monthly entries for its entire amortization schedule (one entry per installment, spanning beyond the current calendar year if `numero_cuotas` requires it) at creation time, using each installment's fixed amount from the schedule instead of the copy-last-amount-forward behavior used for other recurring concepts.

#### Scenario: Multi-year debt generates entries beyond the current year
- **WHEN** a debt is created with `numero_cuotas` greater than the number of months remaining in the current calendar year
- **THEN** the system generates monthly entries continuing into the following year(s) until all installments have an entry, not just through December of the current year

#### Scenario: Generated amounts follow the schedule, not a flat copy
- **WHEN** an amortized debt's fixed installment is computed
- **THEN** every auto-generated entry for that debt uses that fixed installment amount as `monto_planeado`, consistent across all its months

#### Scenario: Non-amortized recurring concepts are unaffected
- **WHEN** a `deuda` concept without amortization data, or a `gasto_fijo` concept, is created or edited
- **THEN** auto-generation continues to behave exactly as before this change (copy-last-amount-forward through December of the current year)
