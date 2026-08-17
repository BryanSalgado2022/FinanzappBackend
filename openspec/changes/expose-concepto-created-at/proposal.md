## Why

The frontend's Concept Detail screen needs each concept's creation date to cap how far back a user can navigate its year selector (no concept should be browsable before it existed). `Concepto.created_at` already exists on the model but isn't exposed in the API.

## What Changes

- `GET /concepts`, `GET /concepts/{id}`, and `POST /concepts` responses (all built via `ConceptoRead`) now include `created_at`.
- No new logic - `created_at` is already set automatically at creation; this only exposes an existing value.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `budget-concepts`: concept responses include their creation timestamp.

## Impact

- `app/schemas/concepto.py`: `ConceptoRead` gains `created_at: datetime`.
- `app/routers/concepts.py`: `_to_read` passes `concepto.created_at`.
