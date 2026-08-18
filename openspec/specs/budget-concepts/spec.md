# budget-concepts Specification

## Purpose
Lets each user define and manage the recurring financial line items (debts, fixed expenses, income sources) that make up their personal budget, replacing the hand-maintained rows of their spreadsheet.

## Requirements

### Requirement: Create a concept
The system SHALL allow an authenticated user to create a concept with a free-form name, a type (`deuda`, `gasto_fijo`, or `ingreso`), and zero or more category assignments by id, referencing categories owned by that user.

#### Scenario: Create a fixed-expense concept
- **WHEN** a user creates a concept with type `gasto_fijo`, a name, and no categories
- **THEN** the system saves the concept as active, owned by that user, with no categories assigned

#### Scenario: Create a concept with a category
- **WHEN** a user creates a concept and supplies one or more category ids that belong to that user
- **THEN** the system assigns all of those categories to the concept

#### Scenario: Reject a category id that does not belong to the user
- **WHEN** a user attempts to create or update a concept referencing a category id that does not exist or belongs to a different user
- **THEN** the system rejects the request and does not create or modify the concept

#### Scenario: Reject a concept with an invalid type
- **WHEN** a user attempts to create a concept with a type other than `deuda`, `gasto_fijo`, or `ingreso`
- **THEN** the system rejects the request and does not create the concept

### Requirement: Debt concepts track a total amount
The system SHALL allow a concept of type `deuda` to have a `valor_total` (total amount owed) and SHALL reject `valor_total` on concepts of type `gasto_fijo` or `ingreso`.

#### Scenario: Create a debt with a total amount
- **WHEN** a user creates a concept of type `deuda` with a `valor_total`
- **THEN** the system saves the `valor_total` on the concept

#### Scenario: Total amount rejected on non-debt concept
- **WHEN** a user attempts to set `valor_total` on a concept of type `gasto_fijo` or `ingreso`
- **THEN** the system rejects the request

### Requirement: Debt remaining balance
The system SHALL compute a debt concept's remaining balance as its effective starting amount minus the sum of `monto_pagado` across every monthly entry ever recorded for that concept, regardless of year, and SHALL NOT reset this balance when the calendar year changes. For a debt with amortization data and no starting installment set (or a starting installment of 1), the effective starting amount is `valor_total`. For a debt with amortization data and a starting installment greater than 1, the effective starting amount is the schedule's balance immediately after the installment preceding the starting one, since no entries or payments exist in the system for the skipped installments.

#### Scenario: Remaining balance reflects payments across years
- **WHEN** a debt concept has payments recorded in more than one calendar year
- **THEN** the system's reported remaining balance subtracts all of those payments from its effective starting amount, not just the current year's

#### Scenario: Debt fully paid off
- **WHEN** the sum of a debt concept's recorded payments reaches its effective starting amount
- **THEN** the system reports a remaining balance of zero (not negative, if payments exactly match)

#### Scenario: Remaining balance for a debt with a starting installment
- **WHEN** an amortized debt has a starting installment greater than 1
- **THEN** the reported remaining balance is computed from the schedule's balance at that starting point, not from the full original `valor_total`

### Requirement: List and retrieve concepts
The system SHALL allow a user to list all of their concepts and retrieve a single concept by id, including its current type, assigned categories (each with its id, `nombre`, and `emoji`), status, and (for debts) remaining balance.

#### Scenario: List concepts
- **WHEN** a user requests their list of concepts
- **THEN** the system returns only concepts owned by that user

#### Scenario: Retrieved concept includes its categories
- **WHEN** a user retrieves a concept that has one or more categories assigned
- **THEN** the response includes each assigned category's id, name, and emoji (if set)

### Requirement: Update and finish a concept
The system SHALL allow a user to update a concept's name, category assignments, or status, and SHALL allow marking a concept as finished so it stops being treated as an active recurring item.

#### Scenario: Mark a debt as finished
- **WHEN** a user marks a fully paid debt concept as finished
- **THEN** the system stops including that concept when auto-generating future monthly entries, while preserving its historical entries

#### Scenario: Replace a concept's category assignments
- **WHEN** a user updates a concept with a new list of category ids
- **THEN** the system replaces the concept's prior category assignments with exactly the categories in the new list

#### Scenario: Concept persists across years by default
- **WHEN** a calendar year ends and an active concept has not been marked finished or deleted
- **THEN** the concept remains active and available for the new year without the user recreating it

### Requirement: Delete a concept
The system SHALL allow a user to delete a concept they own.

#### Scenario: Delete a concept
- **WHEN** a user deletes one of their concepts
- **THEN** the system removes it from their active concept list

### Requirement: Debt concepts can define amortization terms
The system SHALL allow a concept of type `deuda` to optionally specify `tasa_interes` (a numeric interest rate), `periodo_tasa` (`mensual` or `anual`, indicating how `tasa_interes` is expressed), and `numero_cuotas` (total installment count). The system SHALL require `tasa_interes` and `numero_cuotas` together: providing one without the other SHALL be rejected. These fields SHALL be rejected on concepts of type `gasto_fijo` or `ingreso`.

#### Scenario: Create a debt with full amortization terms
- **WHEN** a user creates a `deuda` concept with `valor_total`, `tasa_interes`, `periodo_tasa`, and `numero_cuotas` all provided
- **THEN** the system saves the concept with its amortization terms

#### Scenario: Reject interest rate without installment count
- **WHEN** a user attempts to create a `deuda` concept with `tasa_interes` but no `numero_cuotas`
- **THEN** the system rejects the request

#### Scenario: Reject installment count without interest rate
- **WHEN** a user attempts to create a `deuda` concept with `numero_cuotas` but no `tasa_interes`
- **THEN** the system rejects the request

#### Scenario: Amortization terms remain optional
- **WHEN** a user creates a `deuda` concept with only `valor_total` and no amortization fields
- **THEN** the system saves the concept exactly as before this change, with no amortization schedule

### Requirement: Fixed installment computed for amortized debts
The system SHALL, when a debt concept has both `tasa_interes` and `numero_cuotas`, compute a fixed monthly installment amount using the standard fixed-installment (French) amortization method, converting `tasa_interes` to a monthly rate first when `periodo_tasa` is `anual`, and SHALL generate the full installment-by-installment amortization schedule (interest portion, principal portion, and resulting balance per installment).

#### Scenario: Annual rate is converted before calculating the installment
- **WHEN** a debt is created with `periodo_tasa` set to `anual`
- **THEN** the system converts the annual rate to its equivalent monthly rate before computing the fixed installment, rather than treating the annual number as if it were monthly

#### Scenario: Schedule reflects declining balance
- **WHEN** the amortization schedule is generated for a debt
- **THEN** each successive installment's interest portion is computed against the declining balance from the prior installment, and the final installment's ending balance is zero

### Requirement: Financial terms are immutable once amortization data exists
The system SHALL reject changes to `valor_total`, `tasa_interes`, `periodo_tasa`, `numero_cuotas`, and `cuota_inicial` on any debt concept that has amortization data set, with a descriptive error explaining that the concept must be deleted and recreated to change these terms. Changing these terms requires deleting the concept and creating a new one.

#### Scenario: Reject editing the amount of an amortized debt
- **WHEN** a user attempts to update `valor_total` on a debt concept that has `tasa_interes` and `numero_cuotas` set
- **THEN** the system rejects the request without changing the concept

#### Scenario: Reject editing the starting installment
- **WHEN** a user attempts to update `cuota_inicial` on an existing debt concept
- **THEN** the system rejects the request with a message explaining that the concept must be deleted and recreated to change it, without changing the concept

#### Scenario: Non-amortized debts remain editable as before
- **WHEN** a user updates `valor_total` on a debt concept that has no amortization data
- **THEN** the system accepts the change, unchanged from prior behavior

### Requirement: Fixed-duration recurring concepts
The system SHALL allow a concept of type `gasto_fijo` or `ingreso` to optionally specify `duracion_meses` (a number of months), and SHALL reject `duracion_meses` on concepts of type `deuda`.

#### Scenario: Create a fixed-duration income
- **WHEN** a user creates an `ingreso` concept with `duracion_meses` set
- **THEN** the system saves the concept with that duration

#### Scenario: Duration remains optional
- **WHEN** a user creates a `gasto_fijo` or `ingreso` concept without `duracion_meses`
- **THEN** the system saves the concept exactly as before this change, with indefinite/open-ended recurrence

#### Scenario: Reject duration on a debt
- **WHEN** a user attempts to set `duracion_meses` on a `deuda` concept
- **THEN** the system rejects the request

### Requirement: Debt and fixed-expense concepts can define a due day
The system SHALL allow a concept of type `deuda` or `gasto_fijo` to optionally specify `dia_vencimiento`, an integer day-of-month between 1 and 28, and SHALL reject `dia_vencimiento` on concepts of type `ingreso`. `dia_vencimiento` SHALL be settable at creation and editable at any time thereafter — it is not subject to the immutability rule that applies to amortization terms, since changing it does not require recalculating any schedule.

#### Scenario: Set a due day on a debt
- **WHEN** a user creates or updates a `deuda` concept with `dia_vencimiento` set to a value between 1 and 28
- **THEN** the system saves that value on the concept

#### Scenario: Set a due day on a fixed expense
- **WHEN** a user creates or updates a `gasto_fijo` concept with `dia_vencimiento` set to a value between 1 and 28
- **THEN** the system saves that value on the concept

#### Scenario: Reject a due day outside the valid range
- **WHEN** a user attempts to set `dia_vencimiento` to a value less than 1 or greater than 28
- **THEN** the system rejects the request

#### Scenario: Reject a due day on an income concept
- **WHEN** a user attempts to set `dia_vencimiento` on a concept of type `ingreso`
- **THEN** the system rejects the request

#### Scenario: Due day remains editable after creation
- **WHEN** a user updates `dia_vencimiento` on an existing `deuda` or `gasto_fijo` concept, including one with amortization data set
- **THEN** the system accepts the change, independent of whether the concept's financial terms are otherwise locked

#### Scenario: Due day remains optional
- **WHEN** a user creates a `deuda` or `gasto_fijo` concept without `dia_vencimiento`
- **THEN** the system saves the concept exactly as before this change, with no due day set

### Requirement: Concept responses include their creation timestamp
The system SHALL include a `created_at` timestamp on every concept returned to a user, reflecting when that concept was originally created.

#### Scenario: Retrieved concept includes creation timestamp
- **WHEN** a user retrieves a concept they own, whether via listing or fetching it by id
- **THEN** the response includes the `created_at` timestamp recorded when the concept was created

### Requirement: Debt concepts can start partway through an existing amortization schedule
The system SHALL allow a debt concept with amortization data to optionally specify `cuota_inicial`, the installment number at which entry generation should begin, and SHALL reject `cuota_inicial` on a concept without amortization data or outside the range 1 to `numero_cuotas`. When set, only installments from `cuota_inicial` through `numero_cuotas` SHALL be generated as monthly entries; earlier installments are treated as already settled outside the system.

#### Scenario: Create a debt already partway through its schedule
- **WHEN** a user creates a `deuda` concept with amortization data and `cuota_inicial` set to a value greater than 1
- **THEN** the system generates monthly entries only for installments from `cuota_inicial` through `numero_cuotas`, starting at the concept's creation month

#### Scenario: Starting installment remains optional
- **WHEN** a user creates an amortized debt without specifying `cuota_inicial`
- **THEN** the system generates the full schedule starting at installment 1, exactly as before this change

#### Scenario: Reject a starting installment out of range
- **WHEN** a user attempts to set `cuota_inicial` to less than 1 or greater than `numero_cuotas`
- **THEN** the system rejects the request

#### Scenario: Reject a starting installment without amortization data
- **WHEN** a user attempts to set `cuota_inicial` on a concept that does not have both `tasa_interes` and `numero_cuotas`
- **THEN** the system rejects the request
