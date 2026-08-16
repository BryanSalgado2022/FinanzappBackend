# Finanzapp Backend

API en FastAPI para el MVP de Finanzapp: registro de deudas, gastos fijos e ingresos, con presupuesto mensual y balance neto automático. Reemplaza el proceso manual del Excel `Presupuesto1`.

Ver la planeación completa (por qué, requisitos, decisiones técnicas) en `openspec/changes/add-budget-mvp/` — `proposal.md`, `specs/`, `design.md`, `tasks.md`.

## Stack

- **FastAPI** + **SQLModel** (SQLAlchemy + Pydantic) sobre **PostgreSQL**
- **Alembic** para migraciones
- **Google OAuth** para login (el frontend obtiene un ID token de Google; el backend lo verifica y emite su propio JWT)
- Repo hermano `FinanzappFrontend` (React) consume esta API — fuera de este repo

## Estructura

```
app/
  main.py            # instancia FastAPI, registra routers
  config.py          # settings desde variables de entorno (.env)
  database.py        # engine y sesión de SQLModel
  dependencies.py     # dependencia get_current_user (valida JWT)
  models/            # tablas: User, Concepto, EntradaMensual
  schemas/           # request/response (Pydantic)
  services/          # lógica de negocio (auth, conceptos, entradas, resumen)
  routers/           # endpoints HTTP
alembic/             # migraciones
tests/                # pytest (SQLite en memoria, Google auth mockeado)
openspec/             # planeación spec-driven (proposal/specs/design/tasks)
```

## Correr en local con Docker (recomendado)

1. Copia `.env.example` a `.env` y completa `GOOGLE_CLIENT_ID` y `JWT_SECRET` (para desarrollo local, `DATABASE_URL` ya viene apuntando al Postgres de docker-compose). `CORS_ORIGINS` ya trae `http://localhost:5173` (el dev server de `FinanzappFrontend`) por defecto — agrega ahí la URL de producción del frontend cuando la despliegues.
2. Levanta todo:
   ```bash
   docker compose up -d --build
   ```
3. Aplica las migraciones dentro del contenedor:
   ```bash
   docker compose exec api alembic upgrade head
   ```
4. La API queda en `http://localhost:8000`, docs interactivas en `http://localhost:8000/docs`.

Nota: Postgres se expone en el puerto **5433** del host (no 5432), porque 5432 puede estar ocupado por otra instancia local de Postgres. El contenedor `api` se conecta a `db` por la red interna de Docker en el puerto 5432 normal.

## Correr en local sin Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d db        # solo la base de datos
export $(grep -v '^#' .env | xargs)
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
source .venv/bin/activate
python -m pytest -q
```

Los tests usan SQLite en memoria (no requieren Postgres levantado) y mockean la verificación de Google (no requieren credenciales reales). Cubren autenticación/autorización, CRUD de conceptos (incluyendo saldo restante de deudas multi-año), y entradas mensuales + resumen (incluyendo la fórmula de balance verificada contra los números reales del Excel del usuario).

## Autenticación

El frontend hace el login con Google (Google Identity Services) y obtiene un **ID token**. Ese token se envía a:

```
POST /auth/google
{ "id_token": "<google-id-token>" }
```

El backend lo verifica contra `GOOGLE_CLIENT_ID`, crea el usuario si es la primera vez, y devuelve un JWT propio:

```
{ "access_token": "...", "token_type": "bearer" }
```

Ese JWT se manda en cada request subsecuente como `Authorization: Bearer <token>`.

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/google` | Login con Google, devuelve JWT propio |
| POST | `/concepts` | Crear concepto (deuda / gasto_fijo / ingreso) |
| GET | `/concepts` | Listar conceptos del usuario autenticado |
| GET | `/concepts/{id}` | Ver un concepto (incluye saldo restante si es deuda) |
| PATCH | `/concepts/{id}` | Actualizar nombre/categoría/estado/valor_total |
| DELETE | `/concepts/{id}` | Eliminar concepto |
| GET | `/concepts/{id}/entries` | Listar entradas mensuales de un concepto |
| PUT | `/concepts/{id}/entries/{anio}/{mes}` | Crear/actualizar el monto planeado/pagado de un mes |
| GET | `/summary?anio=&mes=` | Balance neto del mes (ingresos - deudas - gastos fijos) |

Ver el contrato completo y ejemplos en `/docs` (Swagger) una vez la API está corriendo.

## Decisiones clave a recordar

- El saldo restante de una deuda se calcula al vuelo (no se cachea) y se acumula entre años — nunca se reinicia el 1 de enero.
- Crear un concepto `deuda`/`gasto_fijo` con `monto_planeado` autogenera las entradas del mes actual hasta diciembre del año en curso, sin sobreescribir meses que el usuario ya haya personalizado.
- El backlog explícito (fuera de este MVP) está documentado en `openspec/changes/add-budget-mvp/proposal.md`: categorización de gastos por IA en lenguaje natural, amortización real de deudas (tasa/cuotas), multi-moneda, reportes y export a Excel/PDF.
