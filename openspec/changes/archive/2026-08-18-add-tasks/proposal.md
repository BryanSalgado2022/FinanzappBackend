## Why

The user wants generic reminders/appointments ("Tareas / citas") independent of the app's financial concepts — a plain to-do with an optional date, time, and note — inspired by a reference app they liked. This is the first of three related future-facing ideas noted on 2026-08-18; the other two (a calendar-view "Agenda" and "Deudores") are explicitly out of scope and will build on this later if pursued.

## What Changes

- Add a new `Tarea` entity per user: `titulo` (required), `emoji` (optional, from a fixed curated set distinct from the category emoji set), `fecha` (optional date), `hora` (optional time, independent of `fecha`), `nota` (optional free text), `completada` (boolean, defaults to false).
- Add full CRUD endpoints: create, list, get, update (including toggling `completada`), delete.
- Task responses include a computed `vencida` flag (overdue: has a past `fecha` and is not `completada`), mirroring the existing pattern for monthly entries.
- No recurrence/frequency field or logic — deliberately omitted until the future "Agenda" calendar view exists to make repeated instances meaningful.
- No integration with any existing screen or endpoint (Dashboard, concepts, summary) — tasks are entirely standalone.

## Capabilities

### New Capabilities
- `task-management`: CRUD for the `Tarea` entity (create, list, get, update, delete), including the overdue computation.

## Impact

- Backend only: new `app/models/tarea.py`, `app/schemas/tarea.py`, `app/services/tarea_service.py`, `app/routers/tareas.py`, and a new Alembic migration (pure schema addition, no data migration needed).
- No frontend changes in this change — a separate frontend change will consume the new endpoints once this is applied.
- No changes to any existing capability or endpoint.
