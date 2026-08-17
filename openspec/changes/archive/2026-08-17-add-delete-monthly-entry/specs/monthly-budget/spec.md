## ADDED Requirements

### Requirement: A monthly entry can be individually deleted
The system SHALL allow a user to delete a single monthly entry of a concept, restoring that month to having no entry at all. This SHALL only be allowed for concepts without a fixed window (no `duracion_meses`, no amortization data) - deletion SHALL be rejected for a concept with amortization data or `duracion_meses` set, since removing one installment from a generated schedule would leave an incoherent gap in it.

#### Scenario: Delete a mistakenly added entry
- **WHEN** a user deletes a monthly entry belonging to an indefinite recurring concept
- **THEN** the system removes that entry, and the month subsequently reports as having no entry

#### Scenario: Reject deletion on a fixed-window concept
- **WHEN** a user attempts to delete a monthly entry belonging to a concept with amortization data or `duracion_meses` set
- **THEN** the system rejects the request without deleting the entry

#### Scenario: Deleting a non-existent entry
- **WHEN** a user attempts to delete a monthly entry for a year/month that has no entry
- **THEN** the system rejects the request with a not-found error

#### Scenario: A deleted entry is not specially protected from re-generation
- **WHEN** the deleted entry was for the real current month of an indefinite recurring concept, and an earlier entry exists to copy an amount from
- **THEN** the system's existing year-extension behavior may regenerate that month's entry the next time the concept's entries are listed, unchanged from that behavior's normal rules
