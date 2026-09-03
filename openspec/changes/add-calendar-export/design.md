## Context

The frontend's `agendaEvents.ts` already defines the canonical event categories (concepto due date + payoff celebration, concepto_cierre, gasto, tarea, deudor_inicio, abono, deudor_cierre) computed client-side from data the frontend has already fetched. The backend has no equivalent "all events for a user" query today — each entity (concepts+entries, gastos, tareas, deudores+abonos) is queried independently. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- One shared ICS-generation code path used by both the authenticated download and the token-based subscribe endpoint.
- No new dependency — the iCalendar format for simple all-day events is a small, stable text format.

**Non-Goals:**
- Exactly replicating the frontend's "celebración" visual/emoji treatment — the calendar export just needs clear, informative event titles, not pixel parity with the in-app calendar.
- Two-way sync (calendar app writing back into TOBE) — this is export-only, per the grilled decision to use the universal .ics standard instead of a provider-specific OAuth integration.

## Decisions

**Server-side event computation, independent of the frontend.** `app/services/ics_service.py` queries the DB directly (mirroring `agendaEvents.ts`'s categories, not importing/sharing code with it since one is Python and one is TypeScript) to build a flat list of `(date, title, description)` tuples for a given user and date range: concept due-date entries + a payoff-celebration event when a debt's `saldo_restante` hits zero on a given paid entry's date (same "find max paid date, gate on zero balance" rule as `findCelebracionPago` in `agendaEvents.ts`, reimplemented in Python), concept `finalizado_en` dates, `Gasto` dates, `Tarea` dates, `Deudor.fecha`, `Abono.fecha`, `Deudor.finalizado_en`.

**Hand-rolled ICS text, no new dependency.** All events are all-day (`DTSTART;VALUE=DATE:YYYYMMDD`), which is simple enough to format directly: a `VCALENDAR` wrapper with one `VEVENT` per event, `UID` derived deterministically from entity type + id + date (stable across regenerations, so calendar apps don't create duplicates on re-sync), `SUMMARY` as the title, `DESCRIPTION` for the amount/context, `DTSTAMP` set to generation time. Text lines are folded/escaped per RFC 5545's minimal requirements (escape commas/semicolons/newlines in `SUMMARY`/`DESCRIPTION`).

**Token storage and format.** `User.ics_token: str | None`, a URL-safe random token (`secrets.token_urlsafe(32)`, matching the existing `JWT_SECRET` generation convention used elsewhere in this project's deploy docs). Generated lazily: `POST /calendar/token` always overwrites with a fresh value (covers both "first time" and "regenerate" — no separate endpoints needed, matching the spec's single endpoint for both scenarios).

**`GET /calendar/subscribe/{token}` has no auth dependency at all** — it's deliberately reachable without a JWT (that's the point, calendar apps can't hold a session), scoped entirely by looking up `User` by `ics_token`. A non-matching token returns 404, not a generic 401, since there's no "authentication" happening to fail — the token either identifies a user or it doesn't.

**Shared response builder.** Both routes call the same `ics_service.generate_ics(session, user) -> str`, differing only in how they resolve `user` (JWT-authenticated vs. token lookup) and the response media type (`text/calendar; charset=utf-8`).

## Risks / Trade-offs

- [Risk] Hand-rolling ICS text risks subtle format bugs some calendar clients are strict about (line folding at 75 octets, `\r\n` line endings). → Mitigation: keep events all-day and simple (no timezones, no recurrence rules, no attendees) — the minimal `VEVENT` subset is well-supported by every major client without needing the format's more exotic corners.
- [Risk] A leaked subscribe URL exposes payment amounts/dates to whoever has it, indefinitely, until regenerated. → Mitigation: this is the accepted trade-off from grilling (token-based, regenerable) — regeneration is a one-click fix once available in the UI (sibling frontend change).
