## Context

Greenfield FastAPI backend (`FinanzappBackend`) with PostgreSQL, no existing code or schema. See proposal.md for motivation. The frontend (`FinanzappFrontend`, React) is a separate repo and a separate future change — this design covers only the API and data model. Target deploy is Railway (containers); local dev should run the same container image via Docker Compose (API + Postgres).

## Goals / Non-Goals

**Goals:**
- A data model and API that directly support the three capabilities in specs/ (`auth`, `budget-concepts`, `monthly-budget`).
- A remaining-debt-balance calculation that is correct across year boundaries without a separate reconciliation step.
- An auto-generation mechanism for recurring monthly entries that never clobbers a month the user already edited.

**Non-Goals:**
- Frontend integration details (separate change).
- Amortization/interest-rate calculations for debts (backlog per proposal.md).
- Any caching/performance optimization beyond straightforward indexed queries — the data volume per user (dozens of concepts, hundreds of monthly entries) does not warrant it yet.

## Decisions

### Data model
Three tables:
- **users**: `id`, `google_sub` (Google's stable subject id, unique), `email`, `name`, `created_at`.
- **concepts**: `id`, `user_id` (FK), `nombre`, `tipo` (enum: `deuda` | `gasto_fijo` | `ingreso`), `categoria` (nullable text, free-form), `valor_total` (nullable numeric, only meaningful when `tipo = deuda`; enforced at the application layer, not a DB constraint, since Postgres CHECK constraints on cross-field enum logic add migration friction for little benefit at this scale), `activo` (bool, default true), `created_at`.
- **monthly_entries**: `id`, `concepto_id` (FK), `anio`, `mes` (1-12), `monto_planeado` (numeric), `monto_pagado` (nullable numeric), `pagado` (bool, default false), unique constraint on (`concepto_id`, `anio`, `mes`) to guarantee one entry per concept per month.

All monetary columns use a fixed-precision numeric type (not float), since these are COP amounts entering balance calculations where rounding errors would compound.

**Alternative considered**: a single polymorphic "transactions" table with a `kind` discriminator instead of separate concept/entry tables. Rejected — concepts (the recurring definition) and monthly entries (the per-month instance) have genuinely different lifecycles and fields; splitting them matches the spec's requirements more directly and keeps queries simpler.

### Remaining debt balance: computed, not stored
A debt concept's remaining balance (`valor_total - sum(monto_pagado)` across all monthly entries, all years) is computed on read via an aggregate query, not persisted as a cached column.

**Rationale**: this guarantees the balance is always consistent with the underlying payments with no risk of a cache going stale after an edit or delete. At this data volume (a handful of debts, at most a few hundred payments each), the aggregate query cost is negligible.

**Alternative considered**: a cached `saldo_restante` column updated by a trigger or service-layer hook on every payment write. Rejected for v1 — it adds a second source of truth that must be kept in sync on every entry create/update/delete, for a performance benefit that isn't needed yet. Revisit if/when this becomes a hot path.

### Auto-generation of future monthly entries
When a recurring concept (`deuda` or `gasto_fijo`, `activo = true`) is created or its current month's `monto_planeado` changes, the service layer upserts monthly entries for every month from the current month through December of the current year, using the new `monto_planeado`, **but only for months that don't already have an entry**. Existing entries (already-recorded past months, or future months the user already edited individually) are never overwritten by this process.

**Rationale**: matches the spec requirement directly and avoids the most likely bug in this feature — silently overwriting a month the user deliberately customized (e.g., "Royal Prestige" in the source spreadsheet has a different amount nearly every month).

### Authentication
Google OAuth handles identity; the backend issues its own short-lived JWT after a successful OAuth exchange, which the frontend then sends as a bearer token on API requests. The backend validates that JWT (not the raw Google token) on every request.

**Rationale**: decouples API auth from Google token lifetimes/refresh semantics, and keeps the auth boundary entirely inside this backend, matching the `auth` spec's requirement that every data endpoint requires a valid session.

**Alternative considered**: validating the Google ID token directly on every API request. Rejected — Google ID tokens are short-lived and re-validating/refreshing them on every call couples this API's session lifetime to Google's, with no benefit for a single-backend system.

## Risks / Trade-offs

- [Floating-point rounding on money amounts] → Mitigated by using fixed-precision numeric columns end to end, never floats, for `valor_total`, `monto_planeado`, `monto_pagado`, and the computed `balance_neto`.
- [Auto-generation runs at year-end and silently stops in December, surprising the user in January] → Out of scope for this change per proposal.md ("annual budget = computed view over 12 months"); the `monthly-budget` spec only requires generation through December of the current year. Note for the frontend change: the UI should prompt or auto-trigger next-year generation, not assume it happens silently server-side.
- [Concurrent edits to the same month (e.g., two requests racing on the create-or-update of a monthly entry)] → Mitigated by the unique constraint on (`concepto_id`, `anio`, `mes`) plus an upsert (insert-or-update) operation instead of separate exists-check-then-insert logic.
- [`valor_total` set on a non-debt concept via a direct API call bypassing validation] → Mitigated by application-layer validation on every write path (create and update), covered by the `budget-concepts` spec scenario for rejecting this case.

## Migration Plan

Greenfield project — no data migration risk. Deployment steps:
1. Initial Alembic migration creates `users`, `concepts`, `monthly_entries` with the constraints above.
2. Environment variables required: database URL, Google OAuth client id/secret, JWT signing secret.
3. Deploy as a container to Railway; local dev mirrors this via Docker Compose (API + Postgres) so behavior matches between environments.
4. No rollback complexity beyond standard Alembic downgrade, since there is no production data yet.

## Open Questions

- Exact JWT library/session-expiry duration (e.g., `python-jose` vs `pyjwt`, access-token lifetime) — an implementation detail that doesn't change the `auth` spec's externally observable behavior; decide during implementation.
- Whether `pagado` is stored as an explicit boolean column or derived from `monto_pagado is not null` — an internal representation choice; either satisfies the `monthly-budget` spec as written. Decide during implementation.
