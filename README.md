# Finanzapp Backend

API en FastAPI para el MVP de Finanzapp: registro de deudas, gastos fijos e ingresos, con presupuesto mensual y balance neto automático. Reemplaza el proceso manual del Excel `Presupuesto1`.

Ver la planeación completa (por qué, requisitos, decisiones técnicas) en `openspec/specs/` (specs vigentes) y en los changes archivados: `openspec/changes/archive/2026-08-15-add-budget-mvp/` (MVP original) y `openspec/changes/add-debt-amortization/` (amortización de deudas + resúmenes).

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

1. Copia `.env.example` a `.env` y completa `GOOGLE_CLIENT_ID` y `JWT_SECRET` (para desarrollo local, `DATABASE_URL` ya viene apuntando al Postgres de docker-compose). `CORS_ORIGINS` ya trae `http://localhost:5173` (el dev server de `FinanzappFrontend`) por defecto — agrega ahí la URL de producción del frontend cuando la despliegues. Si Google OAuth real no está disponible (p. ej. mientras se propaga un cambio en Google Cloud Console), pon `DEV_MODE=true` para habilitar `POST /auth/dev-login`, que hace login sin pasar por Google — **nunca actives esto fuera de tu máquina local**.
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
| POST | `/auth/dev-login` | Login sin Google, solo si `DEV_MODE=true` (404 si no) |
| POST | `/concepts` | Crear concepto (deuda / gasto_fijo / ingreso; deudas aceptan `tasa_interes`+`periodo_tasa`+`numero_cuotas` opcionales) |
| GET | `/concepts` | Listar conceptos del usuario autenticado |
| GET | `/concepts/{id}` | Ver un concepto (incluye saldo restante y, si tiene amortización, `cuota_fija`) |
| PATCH | `/concepts/{id}` | Actualizar nombre/categoría/estado/valor_total/dia_vencimiento (valor_total no editable si la deuda tiene amortización; dia_vencimiento siempre editable) |
| DELETE | `/concepts/{id}` | Eliminar concepto (elimina también sus entradas mensuales) |
| GET | `/concepts/{id}/entries` | Listar entradas mensuales de un concepto |
| PUT | `/concepts/{id}/entries/{anio}/{mes}` | Crear/actualizar el monto planeado/pagado de un mes |
| GET | `/summary?anio=&mes=` | Balance neto del mes (ingresos - deudas - gastos fijos) |
| GET | `/summary/annual?anio=` | Ingresos/gastos planeados por cada uno de los 12 meses del año |
| GET | `/debts/summary` | Total adeudado, total pagado, % de progreso global y composición entre todas las deudas del usuario |

Ver el contrato completo y ejemplos en `/docs` (Swagger) una vez la API está corriendo.

## Decisiones clave a recordar

- El saldo restante de una deuda se calcula al vuelo (no se cachea) y se acumula entre años — nunca se reinicia el 1 de enero.
- Crear un concepto `deuda`/`gasto_fijo`/`ingreso` con `monto_planeado` (sin amortización ni duración fija) autogenera las entradas del mes actual hasta diciembre del año en curso, sin sobreescribir meses que el usuario ya haya personalizado. `ingreso` funciona igual que `gasto_fijo` en este aspecto (antes no autogeneraba nada).
- Una deuda con `tasa_interes` + `numero_cuotas` calcula la cuota fija (método francés) y genera **todo** el cronograma de una vez (puede cruzar años). `tasa_interes` anual se convierte a mensual con la fórmula de tasa efectiva (no `/12`), igual que la reportan los bancos colombianos.
- `gasto_fijo`/`ingreso` pueden llevar `duracion_meses` (opcional, no aplica a `deuda`): genera exactamente esa cantidad de meses de una vez, igual que una amortización pero con un monto fijo repetido, y luego deja de generar — útil para un ingreso o gasto temporal con fecha de fin conocida.
- `valor_total`, `tasa_interes`, `periodo_tasa`, `numero_cuotas` y `duracion_meses` quedan **inmutables** una vez creado el concepto — para cambiar condiciones, se elimina el concepto y se crea uno nuevo (decisión explícita del usuario para evitar lógica de recálculo).
- `deuda`/`gasto_fijo` pueden llevar `dia_vencimiento` (1-28, opcional, no aplica a `ingreso`) — a diferencia de los campos anteriores, es **siempre editable** porque es puramente informativo y no dispara ningún recálculo. Cada entrada mensual expone `vencida` (calculado al vuelo: no pagada y con fecha de vencimiento ya pasada).
- El backlog explícito está documentado en `openspec/changes/archive/2026-08-15-add-debt-amortization/proposal.md`: presupuesto por categorías tipo sobres (Necesidades/Deseos/Deudas/Futuro), función de importar datos, categorización de gastos por IA en lenguaje natural, multi-moneda.
