## MODIFIED Requirements

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
