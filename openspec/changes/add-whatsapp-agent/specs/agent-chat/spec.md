## MODIFIED Requirements

### Requirement: A recognized action is proposed, never executed
The system SHALL NOT create, update, or delete any Gasto, Concepto, Tarea, Deudor, or Abono as a result of a chat message. When the model determines the message maps to one of the five supported actions with all required fields present, the system SHALL return a structured proposed action (entity type and extracted fields) instead of executing it.

#### Scenario: A complete message produces a proposal, not a write
- **WHEN** the user's message contains everything required for one of the five supported actions (e.g. "Hoy gasté 50.000 en gasolina" has enough for a Gasto)
- **THEN** the response is a proposed action with the extracted fields, and no row is created in any table

#### Scenario: Proposal fields map to the real creation schema
- **WHEN** a proposed action is returned for a given entity type
- **THEN** its fields correspond one-to-one with that entity's existing creation fields (minus category assignment, out of scope for this capability), so the caller can submit them to the existing creation endpoint unchanged

#### Scenario: A concepto proposal can express a one-time or ongoing recurrence
- **WHEN** the user's message describes a gasto_fijo or ingreso concepto that clearly happens only once (e.g. "hoy me llegaron 100.000 por un regalo") versus one that clearly repeats indefinitely (e.g. "me llegan 1.200.000 cada mes del apartamento arrendado")
- **THEN** the proposed action's fields include `duracion_meses: 1` for the one-time case, and omit `duracion_meses` for the ongoing case
