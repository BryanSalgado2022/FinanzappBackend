## Purpose
Computes how much money a user actually has available right now — as opposed to the monthly summary's full-month plan — by accumulating what's actually been paid and received since a baseline date the user sets, so they don't need to check their bank to know their real cash position.

## ADDED Requirements

### Requirement: Disponible is a running total since the baseline date
The system SHALL compute, for an authenticated user with a configured `saldo_disponible_fecha`, a Disponible figure equal to `saldo_disponible_inicial` plus every paid `ingreso` monthly entry's `monto_pagado` and every abono `interes` dated on or after `saldo_disponible_fecha`, minus every paid `deuda`/`gasto_fijo` monthly entry's `monto_pagado` and every `Gasto.monto` dated on or after `saldo_disponible_fecha`. Disponible SHALL always use `monto_pagado` (the amount actually paid), never `monto_planeado` (the planned amount) — these can differ, per the existing "Recording a payment that differs from the plan" behavior.

#### Scenario: Disponible reflects paid income
- **WHEN** the user has a paid `ingreso` entry dated on or after the baseline date
- **THEN** Disponible includes that entry's `monto_pagado`

#### Scenario: Disponible reflects paid obligations
- **WHEN** the user has a paid `deuda` or `gasto_fijo` entry dated on or after the baseline date
- **THEN** Disponible is reduced by that entry's `monto_pagado`

#### Scenario: A partial payment only reduces Disponible by what was actually paid
- **WHEN** the user marks a `deuda` or `gasto_fijo` entry paid with a `monto_pagado` less than its `monto_planeado` (e.g. planned 100.000, actually paid 50.000)
- **THEN** Disponible is reduced by the 50.000 actually paid, not the 100.000 planned

#### Scenario: Disponible reflects variable expenses
- **WHEN** the user has recorded a `Gasto` dated on or after the baseline date
- **THEN** Disponible is reduced by that expense's amount

#### Scenario: Disponible reflects abono interest
- **WHEN** the user has recorded an abono with an `interes` value dated on or after the baseline date
- **THEN** Disponible includes that interest amount

#### Scenario: Unpaid entries do not affect Disponible
- **WHEN** the user has a pending (unpaid) `ingreso`, `deuda`, or `gasto_fijo` entry
- **THEN** it does not contribute to Disponible, whether or not it's dated after the baseline

#### Scenario: Entries before the baseline date are excluded
- **WHEN** the user has a paid entry, abono interest, or expense dated before `saldo_disponible_fecha`
- **THEN** it does not contribute to Disponible

### Requirement: Disponible is unavailable until configured
The system SHALL report no Disponible figure for a user who has never set `saldo_disponible_inicial`, rather than defaulting to zero or erroring.

#### Scenario: Requesting Disponible before setup
- **WHEN** a user who has never set `saldo_disponible_inicial` requests their Disponible figure
- **THEN** the system reports it as unset, not as zero

### Requirement: Disponible is scoped to the authenticated user
The system SHALL compute Disponible only from the authenticated user's own entries, abonos, and expenses.

#### Scenario: Requests always act on the authenticated user
- **WHEN** an authenticated user requests their Disponible figure
- **THEN** the system only ever aggregates that same user's own records, regardless of any other identifier
