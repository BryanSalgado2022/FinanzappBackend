# debts-summary Specification

## Purpose
Gives the user a single aggregate view across all of their debts (how much they owe in total, how much they've paid, and overall progress) and an annual planned-vs-actual trend, so the app answers "how am I doing this year?" instead of only showing one month or one debt at a time.

## Requirements

### Requirement: Aggregate debt summary
The system SHALL provide, for the authenticated user, a summary across all of their debt concepts: total `valor_total` among debts that have one, total amount paid across all debt entries ever recorded, overall remaining balance, and overall percent progress (amount paid divided by total owed).

#### Scenario: Summary aggregates across multiple debts
- **WHEN** a user has more than one debt concept, each with its own `valor_total` and payment history
- **THEN** the summary reports the sum of all their totals, the sum of all their payments, and a single overall percent progress

#### Scenario: User with no debts
- **WHEN** a user has no debt concepts at all
- **THEN** the summary reports zero totals rather than an error

#### Scenario: Summary is scoped to the authenticated user
- **WHEN** the debt summary is requested
- **THEN** it includes only the requesting user's own debts, never another user's

### Requirement: Debt composition breakdown
The system SHALL include, in the aggregate debt summary, a per-debt breakdown (name, remaining balance) suitable for showing each debt's share of the user's total debt.

#### Scenario: Composition reflects current remaining balances
- **WHEN** the debt composition breakdown is requested
- **THEN** each debt's figure reflects its current remaining balance, consistent with that debt's own remaining-balance calculation

### Requirement: Annual planned-vs-actual trend
The system SHALL provide, for the authenticated user and a given year, the total planned income and total planned expenses (debts + fixed expenses) for each of the 12 months of that year.

#### Scenario: Full-year data for months with entries
- **WHEN** the annual trend is requested for a year that has monthly entries in some months
- **THEN** each of those months reports its actual planned income/expense totals

#### Scenario: Months with no entries report zero
- **WHEN** the annual trend includes a month with no monthly entries at all
- **THEN** that month's totals are reported as zero rather than omitted or erroring
