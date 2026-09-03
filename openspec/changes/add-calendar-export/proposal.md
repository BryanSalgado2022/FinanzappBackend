## Why

The user wants to see payment due dates and other Agenda events in Google Calendar, their phone's calendar, or any tool they prefer — not just inside TOBE. The standard iCalendar (.ics) format works with every major calendar app without requiring TOBE to integrate with each one individually.

## What Changes

- Add `GET /calendar/export`, authenticated the normal way (JWT), returning an `.ics` file for the current user — used by an in-app "Descargar" action.
- Add a per-user regenerable secret token (`ics_token`) and `POST /calendar/token` to (re)generate it, plus `GET /calendar/subscribe/{token}`, a public (no-JWT) endpoint that looks the user up by token and returns the same `.ics` content — used for a "Suscribirse" URL that calendar apps poll automatically. Regenerating the token invalidates any previously issued subscribe URL.
- Both endpoints cover the same window: 3 months back through 12 months forward from today, and the same event set already shown in the in-app Agenda (concept due dates and payoff celebrations, variable expenses, tasks, debtor start/payoff, abonos).

## Capabilities

### New Capabilities
- `calendar-export`: generating and serving the user's events as a standard `.ics` feed, via both an authenticated download and a token-based subscribe URL.

## Impact

- `app/models/user.py`: `ics_token: str | None`.
- New alembic migration adding that nullable column.
- New `app/services/ics_service.py`: builds the event list (mirroring the frontend's `agendaEvents.ts` categories, computed independently server-side from the DB) and formats it as iCalendar text — no new dependency, hand-rolled given the format's simplicity for all-day `VEVENT`s.
- New `app/routers/calendar.py`: `GET /calendar/export` (JWT), `POST /calendar/token` (JWT, generate/regenerate), `GET /calendar/subscribe/{token}` (public, token-scoped).
- `app/schemas/`: new schema for the token response.
