## Purpose

Lets each user define and manage the recurring financial line items (debts, fixed expenses, income sources) that make up their personal budget, replacing the hand-maintained rows of their spreadsheet.

## ADDED Requirements

### Requirement: Create a concept
The system SHALL allow an authenticated user to create a concept with a free-form name, a type (`deuda`, `gasto_fijo`, or `ingreso`), and an optional free-form category.

#### Scenario: Create a fixed-expense concept
- **WHEN** a user creates a concept with type `gasto_fijo`, a name, and no category
- **THEN** the system saves the concept as active, owned by that user, with no category set

#### Scenario: Create a concept with a category
- **WHEN** a user creates a concept and supplies a category value
- **THEN** the system saves that category value on the concept without validating it against a fixed list

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
The system SHALL compute a debt concept's remaining balance as its `valor_total` minus the sum of `monto_pagado` across every monthly entry ever recorded for that concept, regardless of year, and SHALL NOT reset this balance when the calendar year changes.

#### Scenario: Remaining balance reflects payments across years
- **WHEN** a debt concept has payments recorded in more than one calendar year
- **THEN** the system's reported remaining balance subtracts all of those payments from `valor_total`, not just the current year's

#### Scenario: Debt fully paid off
- **WHEN** the sum of a debt concept's recorded payments reaches its `valor_total`
- **THEN** the system reports a remaining balance of zero (not negative, if payments exactly match)

### Requirement: List and retrieve concepts
The system SHALL allow a user to list all of their concepts and retrieve a single concept by id, including its current type, category, status, and (for debts) remaining balance.

#### Scenario: List concepts
- **WHEN** a user requests their list of concepts
- **THEN** the system returns only concepts owned by that user

### Requirement: Update and finish a concept
The system SHALL allow a user to update a concept's name, category, or status, and SHALL allow marking a concept as finished so it stops being treated as an active recurring item.

#### Scenario: Mark a debt as finished
- **WHEN** a user marks a fully paid debt concept as finished
- **THEN** the system stops including that concept when auto-generating future monthly entries, while preserving its historical entries

#### Scenario: Concept persists across years by default
- **WHEN** a calendar year ends and an active concept has not been marked finished or deleted
- **THEN** the concept remains active and available for the new year without the user recreating it

### Requirement: Delete a concept
The system SHALL allow a user to delete a concept they own.

#### Scenario: Delete a concept
- **WHEN** a user deletes one of their concepts
- **THEN** the system removes it from their active concept list
