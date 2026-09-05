## ADDED Requirements

### Requirement: Recalculating amortization terms preserves paid entries and regenerates the rest
The system SHALL, when a debt concept's amortization terms are corrected, leave every already-paid monthly entry completely unchanged (`monto_planeado`, `monto_pagado`, `pagado`, `fecha_pago` all untouched), delete every not-yet-paid entry, and generate a fresh set of entries for the remaining installments using the new terms, continuing the calendar sequence from the month immediately after the latest paid entry (or from the current month, if none has been paid yet).

#### Scenario: Paid entries are untouched by recalculation
- **WHEN** a debt concept has one or more paid entries and its amortization terms are corrected
- **THEN** those paid entries' amounts and paid status remain exactly as they were before the correction

#### Scenario: Unpaid entries are replaced with the new schedule
- **WHEN** a debt concept has unpaid entries (past or future) and its amortization terms are corrected
- **THEN** those entries are removed and replaced with entries computed from the new fixed installment amount

#### Scenario: Regeneration continues the calendar sequence after the last paid entry
- **WHEN** a debt concept with paid entries through a given month has its terms corrected
- **THEN** the newly generated entries begin the month immediately following that last paid month, without a gap or overlap

#### Scenario: Regeneration starts from today when nothing has been paid
- **WHEN** a debt concept with no paid entries yet has its amortization terms corrected
- **THEN** the newly generated entries begin at the current month, same as at creation time
