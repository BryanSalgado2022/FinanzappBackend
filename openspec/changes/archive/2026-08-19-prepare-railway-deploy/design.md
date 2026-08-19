## Context

See proposal.md - Why. Today's `Dockerfile` is a plain `python:3.12-slim` single-stage build with a hardcoded `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`; migrations are applied manually via `docker compose exec api alembic upgrade head`. `docker-compose.yml` maps host port 8000 to the container's fixed 8000 for local dev - that mapping is independent of whatever port the container listens on internally, so changing the container's listen port doesn't break local dev as long as compose still maps to whatever the container ends up using locally. Tests (`tests/conftest.py`) already force `sqlite://` in-memory and `DEV_MODE=false` at import time, so CI needs no database service and no `.env` file.

## Goals / Non-Goals

**Goals:**
- One image works both for local `docker compose up` and for a Railway deploy, with no separate Dockerfile.
- Every deploy applies pending migrations automatically, with no manual step to forget.
- CI catches a broken backend before it reaches `main`.
- The user has an exact, copy-pasteable list of what to configure in Railway's dashboard - I do not touch Railway itself.

**Non-Goals:**
- Not building a Railway config file (`railway.json`/`railway.toml`) - Railway can build directly from the `Dockerfile` it finds when the user connects the repo; no extra config file is needed for that.
- Not changing `docker-compose.yml` or the local dev workflow (still a fixed port 8000, still manual migrations if the user wants them - the new automatic-on-boot behavior applies wherever the image runs, local dev included, since the same `CMD` runs either way, but this isn't disruptive: local Postgres, if already at `head`, sees a no-op `alembic upgrade head`).
- Not adding a CD (auto-deploy) step to the GitHub Actions workflow - Railway's own GitHub integration handles deploys once the user connects it from their dashboard; this workflow is CI (tests) only.
- Not adding pytest-cov reporting/thresholds to CI - just a pass/fail test run, matching what exists locally.

## Decisions

**Single `CMD`, shell form, `exec`, default port.** Replace the Dockerfile's `CMD` with:
```dockerfile
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```
- `alembic upgrade head &&` runs migrations first; if they fail, the container exits instead of serving with a stale schema.
- `exec uvicorn ...` replaces the shell process (PID 1) with uvicorn, so it receives `SIGTERM` directly for a clean shutdown - without `exec`, the shell stays PID 1 and uvicorn only gets signals forwarded (or not) depending on the shell, which can cause slow/unclean stops on Railway redeploys.
- `${PORT:-8000}` reads Railway's injected `$PORT` when present, falling back to `8000` for local `docker compose up` (which doesn't set `$PORT`) - so the same image and the same `Dockerfile` serve both environments unchanged.
*Alternative considered*: a separate `docker-entrypoint.sh` script. Rejected as unnecessary ceremony for a single `&&`-chained command; revisit if the startup sequence grows a third step.

**No `railway.toml`/`railway.json`.** Railway auto-detects a `Dockerfile` at the repo root and builds from it directly - no extra platform config file is needed for the build step itself. The only Railway-side configuration is environment variables and the `$PORT` Railway injects automatically at runtime (already handled by the `CMD` change above). This keeps the repo platform-agnostic beyond the `Dockerfile` it already has.

**CI: pytest only, no Postgres service.** The workflow (`.github/workflows/backend-tests.yml`) runs on `push` to `main` and on `pull_request`, using `actions/setup-python` (pin to the same minor version as local dev's `python:3.12-slim`, i.e. `3.12`), `pip install -r requirements.txt`, then `pytest`. No `services:` block for Postgres is needed - `tests/conftest.py` already forces an in-memory SQLite engine before any test runs, independent of `DATABASE_URL`.

**Environment variables to configure in Railway's dashboard** (documented in README, not committed anywhere as real values):
| Variable | Value in Railway |
|---|---|
| `DATABASE_URL` | Railway's own Postgres plugin provides this automatically when attached to the service - copy its reference, don't hand-type it |
| `GOOGLE_CLIENT_ID` | Same value as local `.env` (same Google OAuth client, unless the user creates a separate prod client) |
| `JWT_SECRET` | A new, strong random value - **must not** reuse the local dev secret |
| `CORS_ORIGINS` | The Vercel frontend's production URL, added once that URL exists (chicken-and-egg with the sibling Vercel change - documented as a manual post-deploy step in both repos' design docs) |
| `DEV_MODE` | Left unset, or explicitly `false` - **never** `true` in a deployed environment, since it enables password-less `/auth/dev-login` |

**Port note**: Railway assigns `$PORT` dynamically per deploy; the app must bind to whatever it provides, which the `CMD` change already does. No manual port configuration needed on Railway's side beyond exposing the service.

## Risks / Trade-offs

[`alembic upgrade head` running automatically on every boot, including every container restart/redeploy] → This is the intended behavior (goal, not just accepted risk) - a no-op re-run when already at `head` is cheap and safe; the real risk is a *failing* migration blocking startup, which is desirable (fail loud rather than serve against a stale schema) rather than a trade-off to mitigate.
[`CORS_ORIGINS` can't be set to the real Vercel URL until Vercel assigns one, and vice versa for `VITE_API_BASE_URL` needing Railway's URL] → Documented as an explicit two-step manual sequence in the README: deploy backend first (get its URL), then deploy frontend with that URL, then come back and add the frontend's URL to the backend's `CORS_ORIGINS`.
[No `railway.toml` means Railway's exact build behavior (e.g. build args, health check path) is whatever Railway's dashboard defaults to, not codified] → Acceptable for a first deploy of this size; add `railway.toml` later if the dashboard defaults prove insufficient.
