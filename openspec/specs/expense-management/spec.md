# expense-management Specification

## Purpose
Lets a user record ad-hoc, variable-amount spending that happens on a specific day — a purchase with no monthly plan behind it — so that money leaving their pocket is captured even when it wasn't budgeted in advance.

## Requirements

### Requirement: Record a variable expense
The system SHALL let a user create a `Gasto` with a required `monto`, a required `fecha`, and a required `descripcion`, optionally assigning it zero or more of the user's existing categories.

#### Scenario: Creating a minimal expense
- **WHEN** a user creates a expense with only `monto`, `fecha`, and `descripcion`
- **THEN** the expense is created with no categories assigned

#### Scenario: Creating an expense with categories
- **WHEN** a user creates an expense and assigns one or more of their existing categories to it
- **THEN** the expense is created with exactly those categories assigned

#### Scenario: Date has no range restriction
- **WHEN** a user creates an expense with a `fecha` in the past or in the future relative to today
- **THEN** the system accepts it without rejecting it for being out of range

### Requirement: List and view expenses
The system SHALL let a user list their own expenses filtered by year and month (based on `fecha`), and view a single expense by id.

#### Scenario: Listing expenses for a month
- **WHEN** a user lists expenses for a given year and month
- **THEN** the system returns exactly the user's own expenses whose `fecha` falls in that year and month

#### Scenario: Listing is scoped to the authenticated user
- **WHEN** a user lists expenses
- **THEN** the system never includes another user's expenses in the result

### Requirement: Edit and delete an expense
The system SHALL let a user update any field of their own expense (`monto`, `fecha`, `descripcion`, assigned categories) or delete it, with no restriction based on the expense's date.

#### Scenario: Editing an expense recorded in a past month
- **WHEN** a user edits an expense whose `fecha` is in a previous month
- **THEN** the system applies the edit exactly as it would for an expense dated today

#### Scenario: Deleting an expense
- **WHEN** a user deletes an expense
- **THEN** the expense no longer appears in any subsequent listing or balance calculation

#### Scenario: Changing an expense's categories
- **WHEN** a user edits an expense and changes its selected categories
- **THEN** the expense's category assignments are updated to exactly the newly selected set
