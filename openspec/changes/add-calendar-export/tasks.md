## 1. Model and migration

- [x] 1.1 Add `ics_token: str | None` to `User` in `app/models/user.py`.
- [x] 1.2 Generate and review the alembic migration adding the nullable column.

## 2. ICS generation service

- [x] 2.1 Create `app/services/ics_service.py`: a function collecting all events (concepto due dates + payoff celebration, concepto_cierre, gasto, tarea, deudor_inicio, abono, deudor_cierre) for a user within `[today - 3 months, today + 12 months]`, per design.md.
- [x] 2.2 Add the ICS text formatter: `VCALENDAR`/`VEVENT` wrapper, all-day `DTSTART;VALUE=DATE`, stable `UID`, `SUMMARY`/`DESCRIPTION` with RFC 5545 escaping, `DTSTAMP`.
- [x] 2.3 Add `generate_ics(session, user) -> str` combining both, used by both routes.

## 3. Endpoints

- [x] 3.1 Add `app/schemas/calendar.py` (or similar) with the token response schema.
- [x] 3.2 Create `app/routers/calendar.py`: `GET /calendar/export` (JWT via `get_current_user`, returns `text/calendar` response with `generate_ics`).
- [x] 3.3 Add `POST /calendar/token`: generates a fresh `secrets.token_urlsafe(32)`, overwrites `current_user.ics_token`, returns it.
- [x] 3.4 Add `GET /calendar/subscribe/{token}`: no auth dependency, looks up `User` by `ics_token`, 404 if no match, otherwise returns `generate_ics` for that user.
- [x] 3.5 Register the router in `app/main.py`.

## 4. Tests

- [x] 4.1 Add tests: `GET /calendar/export` requires auth and returns valid-looking ICS content scoped to the user; events outside the 3-month-back/12-month-forward window are excluded; each event category (concept due date, payoff celebration, gasto, tarea, deudor start/payoff, abono) appears when expected.
- [x] 4.2 Add tests for `POST /calendar/token`: first call creates a token; a second call issues a different token and invalidates the first at `/calendar/subscribe/{token}`.
- [x] 4.3 Add tests for `GET /calendar/subscribe/{token}`: valid token returns that user's calendar with no auth header; invalid/unknown token returns 404; cross-user isolation (token only ever returns its own user's events).
- [x] 4.4 Run the full test suite and confirm it passes.
