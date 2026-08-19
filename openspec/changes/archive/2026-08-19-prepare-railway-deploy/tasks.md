## 1. Dockerfile

- [x] 1.1 Replace the `CMD` with the shell-form `alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` command
- [x] 1.2 Verify `docker compose up --build` still starts cleanly locally (migrations no-op since local DB is already at head, server listens on 8000 as before)

## 2. CI workflow

- [x] 2.1 Create `.github/workflows/backend-tests.yml`: triggers on `push` to `main` and `pull_request`, sets up Python 3.12, installs `requirements.txt`, runs `pytest`
- [x] 2.2 Verify the workflow file is valid YAML and matches GitHub Actions schema expectations (actionlint or manual review, since it can't be run locally without pushing)

## 3. Documentation

- [x] 3.1 Add a "Despliegue" section to `README.md`: the environment variable table from design.md, the `DEV_MODE` warning, the two-step CORS/API-URL sequencing note, and a short "connect the repo from Railway's dashboard" pointer (no Railway CLI steps, since the user does this themselves)

## 4. Verification

- [x] 4.1 `docker compose up --build` locally: confirm the API starts, migrations run (check logs for the alembic output), and the app responds on `localhost:8000` as before
- [x] 4.2 `pytest` passes locally (150/150) before pushing, as a sanity check for what CI will run
