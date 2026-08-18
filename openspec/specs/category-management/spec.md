# category-management Specification

## Purpose
Lets each user maintain a reusable, centrally-editable set of categories that can be assigned to any of their concepts, so correcting a name or adding a visual identifier updates everywhere that category is used instead of requiring the user to edit every concept individually.

## Requirements

### Requirement: Create a category
The system SHALL allow an authenticated user to create a category with a required `nombre` and an optional `emoji`, owned by that user.

#### Scenario: Create a category with just a name
- **WHEN** a user creates a category with a `nombre` and no `emoji`
- **THEN** the system saves the category as owned by that user, with no emoji set

#### Scenario: Create a category with an emoji
- **WHEN** a user creates a category with a `nombre` and an `emoji` from the fixed allowed set
- **THEN** the system saves the category with that emoji

#### Scenario: Reject an emoji outside the fixed set
- **WHEN** a user attempts to create or update a category with an `emoji` value that is not one of the fixed allowed emojis
- **THEN** the system rejects the request and does not save the invalid value

#### Scenario: Creating a category with a name that already exists returns the existing one
- **WHEN** a user creates a category with a `nombre` that matches (case-insensitively) a category they already own
- **THEN** the system returns that existing category unchanged, without creating a duplicate

### Requirement: List and retrieve categories
The system SHALL allow a user to list all of their categories and retrieve a single category by id.

#### Scenario: List categories
- **WHEN** a user requests their list of categories
- **THEN** the system returns only categories owned by that user

#### Scenario: Retrieve a category owned by another user
- **WHEN** a user attempts to retrieve a category id that belongs to a different user
- **THEN** the system responds as if the category does not exist

### Requirement: Rename or re-style a category propagates everywhere
The system SHALL allow a user to update a category's `nombre` and/or `emoji`, and the updated values SHALL be reflected immediately for every concept that has that category assigned, since the category's data is stored once and referenced, not duplicated.

#### Scenario: Renaming a category updates every concept using it
- **WHEN** a user renames a category that is assigned to one or more concepts
- **THEN** every one of those concepts subsequently reports the category's new name, with no per-concept update required

#### Scenario: Changing a category's emoji updates every concept using it
- **WHEN** a user sets or changes the `emoji` of a category that is assigned to one or more concepts
- **THEN** every one of those concepts subsequently reports the category's new emoji

### Requirement: Delete a category
The system SHALL allow a user to delete a category they own. Deleting a category SHALL unassign it from every concept that had it, without rejecting the deletion and without leaving any concept in an invalid state.

#### Scenario: Delete an unused category
- **WHEN** a user deletes a category that is not assigned to any concept
- **THEN** the system removes the category and it no longer appears in their category list

#### Scenario: Delete a category in use
- **WHEN** a user deletes a category that is currently assigned to one or more concepts
- **THEN** the system removes the category, and each formerly-assigned concept no longer lists that category but keeps any other categories it had and remains otherwise unaffected
