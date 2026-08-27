## MODIFIED Requirements

### Requirement: Setting the Disponible baseline always re-dates it to today
The system SHALL, whenever a user sets `saldo_disponible_inicial` to a new value, record `saldo_disponible_fecha` as the current server date, regardless of any date supplied by the client. The system SHALL, whenever a user clears `saldo_disponible_inicial` back to `null`, also clear `saldo_disponible_fecha` back to `null`, fully un-configuring Disponible.

#### Scenario: First-time setup
- **WHEN** a user sets `saldo_disponible_inicial` for the first time
- **THEN** the system saves that value with today's date as `saldo_disponible_fecha`

#### Scenario: Re-baselining an existing value
- **WHEN** a user who previously set `saldo_disponible_inicial` sets it again to a new value
- **THEN** the system replaces both the value and `saldo_disponible_fecha` with today's date, discarding the previous baseline date

#### Scenario: Clearing the baseline fully un-configures Disponible
- **WHEN** a user who previously set `saldo_disponible_inicial` clears it back to `null`
- **THEN** the system clears both `saldo_disponible_inicial` and `saldo_disponible_fecha`, and subsequent requests for Disponible report it as unset rather than computing from a zero baseline
