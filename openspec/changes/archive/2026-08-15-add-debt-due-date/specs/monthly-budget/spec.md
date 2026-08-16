## ADDED Requirements

### Requirement: Monthly entries report whether they are overdue
The system SHALL compute, for each monthly entry belonging to a concept with `dia_vencimiento` set, an `vencida` flag that is true when the entry is not `pagado` and the date formed by combining the entry's `anio`/`mes` with the concept's `dia_vencimiento` is before the current date. For entries belonging to a concept without `dia_vencimiento` set, `vencida` SHALL be false.

#### Scenario: Unpaid entry past its due date is overdue
- **WHEN** a monthly entry's concept has `dia_vencimiento` set, the entry is not `pagado`, and its computed due date has already passed
- **THEN** the system reports that entry's `vencida` as true

#### Scenario: Paid entry is never overdue
- **WHEN** a monthly entry is `pagado`, regardless of its computed due date
- **THEN** the system reports that entry's `vencida` as false

#### Scenario: Entry not yet due is not overdue
- **WHEN** a monthly entry's computed due date has not yet passed
- **THEN** the system reports that entry's `vencida` as false

#### Scenario: Entries without a due day configured are never flagged
- **WHEN** a monthly entry's concept has no `dia_vencimiento` set
- **THEN** the system reports that entry's `vencida` as false, regardless of payment status
