## MODIFIED Requirements

### Requirement: Auto-generation uses the amortization schedule for amortized debts
The system SHALL, for a debt concept with amortization data, generate monthly entries for its amortization schedule from its starting installment (installment 1 by default, or `cuota_inicial` when set) through `numero_cuotas` (one entry per installment, spanning beyond the current calendar year if needed) at creation time, using each installment's fixed amount from the schedule instead of the copy-last-amount-forward behavior used for other recurring concepts.

#### Scenario: Multi-year debt generates entries beyond the current year
- **WHEN** a debt is created with `numero_cuotas` greater than the number of months remaining in the current calendar year
- **THEN** the system generates monthly entries continuing into the following year(s) until all installments have an entry, not just through December of the current year

#### Scenario: Generated amounts follow the schedule, not a flat copy
- **WHEN** an amortized debt's fixed installment is computed
- **THEN** every auto-generated entry for that debt uses that fixed installment amount as `monto_planeado`, consistent across all its months

#### Scenario: Non-amortized recurring concepts are unaffected
- **WHEN** a `deuda` concept without amortization data, or a `gasto_fijo` concept, is created or edited
- **THEN** auto-generation continues to behave exactly as before this change (copy-last-amount-forward through December of the current year)

#### Scenario: Generation starts at the debt's starting installment
- **WHEN** an amortized debt has `cuota_inicial` set to a value greater than 1
- **THEN** the system generates entries beginning at that installment rather than installment 1, with the first generated entry landing in the concept's creation month

## ADDED Requirements

### Requirement: Indefinite recurring concepts auto-extend into a new year on demand
The system SHALL, when listing an active, indefinite recurring concept's monthly entries (no `duracion_meses`, no amortization data) and no entry exists for the real current year and month, generate entries from the current month through December of the current year using the planned amount from that concept's most recently dated existing entry, without overwriting any existing entry. If the concept has no existing entry at all, the system SHALL NOT generate anything, since there is no known planned amount to carry forward.

#### Scenario: Visiting a concept in a new year fills the gap
- **WHEN** a user views an indefinite recurring concept's entries and the real current month has no entry, while at least one earlier entry exists
- **THEN** the system generates entries from the current month through December of the current year using the most recent existing entry's planned amount, before returning the list

#### Scenario: Existing entries are never overwritten
- **WHEN** the system generates entries to fill a new year's gap
- **THEN** any month that already has an entry, in that year or otherwise, is left unchanged

#### Scenario: No prior entry means no generation
- **WHEN** an indefinite recurring concept has no existing monthly entries at all
- **THEN** the system does not generate any entries when its entry list is viewed, leaving the gap for the user to fill manually

#### Scenario: Fixed-window concepts are unaffected
- **WHEN** a concept has `duracion_meses` set or has amortization data
- **THEN** viewing its entries never triggers this year-extension behavior, consistent with those concepts' fixed, already-fully-generated window

#### Scenario: A concept whose latest entry is in the future is not backfilled
- **WHEN** an indefinite recurring concept's most recently dated entry is for a month after the real current month
- **THEN** the system does not generate anything, since there is no past gap to catch up from
