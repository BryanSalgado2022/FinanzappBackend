## Purpose

Lets each user keep generic reminders and appointments — independent of any financial concept — with an optional date, time, and note, so day-to-day to-dos ("pay the electric bill", "call the bank") have a home in the app without being tied to a debt, expense, or income entry.

## ADDED Requirements

### Requirement: Create a task
The system SHALL allow an authenticated user to create a task with a required `titulo`, and optional `emoji` (from a fixed allowed set), `fecha`, `hora`, and `nota`. A newly created task SHALL default to `completada: false`.

#### Scenario: Create a task with just a title
- **WHEN** a user creates a task with only a `titulo`
- **THEN** the system saves the task as owned by that user, not completed, with no emoji, date, time, or note set

#### Scenario: Create a task with all optional fields
- **WHEN** a user creates a task with `titulo`, an `emoji` from the fixed allowed set, `fecha`, `hora`, and `nota` all provided
- **THEN** the system saves the task with all of those values

#### Scenario: Date and time are independent
- **WHEN** a user creates a task with only `hora` set and no `fecha`, or only `fecha` set and no `hora`
- **THEN** the system accepts the request and saves the task with exactly the fields provided

#### Scenario: Reject an emoji outside the fixed set
- **WHEN** a user attempts to create or update a task with an `emoji` value that is not one of the fixed allowed task emojis
- **THEN** the system rejects the request and does not save the invalid value

### Requirement: List and retrieve tasks
The system SHALL allow a user to list all of their tasks and retrieve a single task by id, including whether it is overdue.

#### Scenario: List tasks
- **WHEN** a user requests their list of tasks
- **THEN** the system returns only tasks owned by that user

#### Scenario: Retrieve a task owned by another user
- **WHEN** a user attempts to retrieve a task id that belongs to a different user
- **THEN** the system responds as if the task does not exist

### Requirement: Task responses include an overdue flag
The system SHALL report a task as overdue (`vencida: true`) when it has a `fecha` in the past and is not `completada`, and SHALL report `vencida: false` in every other case, including when `fecha` is not set.

#### Scenario: Past-dated, incomplete task is overdue
- **WHEN** a task has a `fecha` before today and `completada` is `false`
- **THEN** the system reports that task as `vencida: true`

#### Scenario: Completed task is never overdue
- **WHEN** a task has a `fecha` before today but `completada` is `true`
- **THEN** the system reports that task as `vencida: false`

#### Scenario: Task without a date is never overdue
- **WHEN** a task has no `fecha` set
- **THEN** the system reports that task as `vencida: false`, regardless of its `completada` status

### Requirement: Update a task
The system SHALL allow a user to update any of a task's fields — `titulo`, `emoji`, `fecha`, `hora`, `nota`, and `completada` — including toggling `completada` to mark it done or not done.

#### Scenario: Mark a task completed
- **WHEN** a user updates a task's `completada` to `true`
- **THEN** the system saves that status and the task no longer reports as overdue even if its date has passed

#### Scenario: Update task details
- **WHEN** a user updates a task's `titulo`, `emoji`, `fecha`, `hora`, or `nota`
- **THEN** the system saves the new values, leaving unspecified fields unchanged

### Requirement: Delete a task
The system SHALL allow a user to delete a task they own.

#### Scenario: Delete a task
- **WHEN** a user deletes one of their tasks
- **THEN** the system removes it from their task list
