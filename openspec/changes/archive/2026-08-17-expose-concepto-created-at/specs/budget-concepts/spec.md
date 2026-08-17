## ADDED Requirements

### Requirement: Concept responses include their creation timestamp
The system SHALL include a `created_at` timestamp on every concept returned to a user, reflecting when that concept was originally created.

#### Scenario: Retrieved concept includes creation timestamp
- **WHEN** a user retrieves a concept they own, whether via listing or fetching it by id
- **THEN** the response includes the `created_at` timestamp recorded when the concept was created
