## Why

The app has no deployment infrastructure today - no CI, no production-hardened Dockerfile, no hosting connected. The frontend just shipped a UI change (collapsible sidebar) that's ready to go live, and the user wants both repos prepared for a real deployment: backend on Railway, frontend on Vercel (a sibling change in FinanzappFrontend). This is pure tooling/infrastructure - no API behavior changes.

## What Changes

- Add a GitHub Actions workflow that runs the existing pytest suite (150 tests, SQLite in-memory, no external services needed) on every push to `main` and every PR.
- Make the container's start command run `alembic upgrade head` before launching uvicorn, so every deploy carries the schema forward automatically instead of requiring a manual `docker compose exec` step.
- Make the start command honor Railway's dynamically-assigned `$PORT` instead of the hardcoded `8000`, while keeping local `docker compose up` working unchanged (port 8000 there comes from the compose file, not the image).
- Document the exact environment variables the user must set in Railway's dashboard, with an explicit warning that `DEV_MODE` must not be set to `true` there (it enables password-less `/auth/dev-login`).
- No application code changes - this is Dockerfile, CI config, and documentation only.

## Capabilities

### New Capabilities
(none - infrastructure/tooling only, no spec-level behavior change; `skip_specs: true` set in `.openspec.yaml`)

### Modified Capabilities
(none)

## Impact

- `Dockerfile`: start command changes to run migrations first and honor `$PORT`.
- `.github/workflows/`: new CI workflow file.
- `README.md`: deployment section documenting required Railway environment variables and the manual account-connection steps the user performs themselves.
- `docker-compose.yml`: unaffected - local dev keeps its own fixed port 8000 and manual-migration workflow unless the user later chooses otherwise.
