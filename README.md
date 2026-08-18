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
| POST | `/auth/register` | Crear cuenta con nombre/email/password (min. 8 caracteres), devuelve JWT. 409 si el email ya existe. Rate-limited. |
| POST | `/auth/login` | Login con email/password, devuelve JWT. 401 genérico si el email no existe o la password no coincide. Rate-limited. |
| POST | `/auth/dev-login` | Login sin Google, solo si `DEV_MODE=true` (404 si no) |
| POST | `/concepts` | Crear concepto (deuda / gasto_fijo / ingreso; deudas aceptan `tasa_interes`+`periodo_tasa`+`numero_cuotas` opcionales; `categoria_ids` opcional para asignar categorías existentes) |
| GET | `/concepts` | Listar conceptos del usuario autenticado |
| GET | `/concepts/{id}` | Ver un concepto (incluye saldo restante, `categorias` completas con emoji, y si tiene amortización, `cuota_fija`) |
| PATCH | `/concepts/{id}` | Actualizar nombre/categorías/estado/valor_total/dia_vencimiento (valor_total no editable si la deuda tiene amortización; dia_vencimiento siempre editable; `categoria_ids` omitido = no tocar, `[]` = quitar todas) |
| DELETE | `/concepts/{id}` | Eliminar concepto (elimina también sus entradas mensuales) |
| GET | `/concepts/{id}/entries` | Listar entradas mensuales de un concepto |
| PUT | `/concepts/{id}/entries/{anio}/{mes}` | Crear/actualizar el monto planeado/pagado de un mes |
| DELETE | `/concepts/{id}/entries/{anio}/{mes}` | Eliminar una entrada mensual individual. Solo en conceptos recurrentes indefinidos (409 si el concepto tiene amortización o `duracion_meses`). 404 si la entrada no existe. |
| GET | `/summary?anio=&mes=` | Balance neto del mes (ingresos - deudas - gastos fijos - gastos variables) |
| GET | `/summary/annual?anio=` | Ingresos/gastos planeados por cada uno de los 12 meses del año |
| GET | `/debts/summary` | Total adeudado, total pagado, % de progreso global y composición entre todas las deudas del usuario |
| POST | `/categorias` | Crear una categoría (nombre + emoji opcional). Idempotente por nombre (case-insensitive): si ya existe, devuelve la existente en vez de duplicar |
| GET | `/categorias` | Listar categorías del usuario autenticado |
| GET | `/categorias/{id}` | Ver una categoría |
| PATCH | `/categorias/{id}` | Renombrar y/o cambiar el emoji de una categoría — se refleja automáticamente en todo concepto que la tenga asignada |
| DELETE | `/categorias/{id}` | Eliminar una categoría. Se desasigna silenciosamente de los conceptos que la tenían, sin bloquear el borrado |
| POST | `/tareas` | Crear una tarea/recordatorio (título requerido; emoji, fecha, hora y nota opcionales) |
| GET | `/tareas` | Listar tareas del usuario autenticado |
| GET | `/tareas/{id}` | Ver una tarea (incluye `vencida`, calculado al vuelo) |
| PATCH | `/tareas/{id}` | Actualizar cualquier campo de una tarea, incluyendo `completada` |
| DELETE | `/tareas/{id}` | Eliminar una tarea |
| POST | `/deudores` | Registrar un deudor (nombre, monto_total y fecha requeridos; garantía opcional) |
| GET | `/deudores` | Listar deudores del usuario autenticado, con `saldo_restante` calculado al vuelo |
| GET | `/deudores/{id}` | Ver un deudor |
| PATCH | `/deudores/{id}` | Actualizar cualquier campo de un deudor, incluyendo `activo` |
| DELETE | `/deudores/{id}` | Eliminar un deudor (elimina también sus abonos) |
| POST | `/deudores/{id}/abonos` | Registrar un abono (pago parcial) para un deudor |
| GET | `/deudores/{id}/abonos` | Listar abonos de un deudor |
| DELETE | `/deudores/{id}/abonos/{abono_id}` | Eliminar un abono |
| POST | `/gastos` | Registrar un gasto variable/puntual (monto, fecha y descripción requeridos; categorías opcionales) |
| GET | `/gastos?anio=&mes=` | Listar gastos del usuario autenticado, opcionalmente filtrados por año/mes de `fecha` |
| GET | `/gastos/{id}` | Ver un gasto |
| PATCH | `/gastos/{id}` | Actualizar cualquier campo de un gasto, sin restricción por fecha |
| DELETE | `/gastos/{id}` | Eliminar un gasto |

Ver el contrato completo y ejemplos en `/docs` (Swagger) una vez la API está corriendo.

## Decisiones clave a recordar

- El saldo restante de una deuda se calcula al vuelo (no se cachea) y se acumula entre años — nunca se reinicia el 1 de enero.
- Crear un concepto `deuda`/`gasto_fijo`/`ingreso` con `monto_planeado` (sin amortización ni duración fija) autogenera las entradas del mes actual hasta diciembre del año en curso, sin sobreescribir meses que el usuario ya haya personalizado. `ingreso` funciona igual que `gasto_fijo` en este aspecto (antes no autogeneraba nada).
- Una deuda con `tasa_interes` + `numero_cuotas` calcula la cuota fija (método francés) y genera **todo** el cronograma de una vez (puede cruzar años). `tasa_interes` anual se convierte a mensual con la fórmula de tasa efectiva (no `/12`), igual que la reportan los bancos colombianos.
- `gasto_fijo`/`ingreso` pueden llevar `duracion_meses` (opcional, no aplica a `deuda`): genera exactamente esa cantidad de meses de una vez, igual que una amortización pero con un monto fijo repetido, y luego deja de generar — útil para un ingreso o gasto temporal con fecha de fin conocida.
- `valor_total`, `tasa_interes`, `periodo_tasa`, `numero_cuotas`, `cuota_inicial` y `duracion_meses` quedan **inmutables** una vez creado el concepto — para cambiar condiciones, se elimina el concepto y se crea uno nuevo (decisión explícita del usuario para evitar lógica de recálculo).
- Una deuda amortizada puede llevar `cuota_inicial` (opcional, 1..`numero_cuotas`) para modelar un crédito que el usuario ya tenía y ya venía pagando antes de usar la app: solo se generan entradas desde esa cuota en adelante (aterrizando en el mes de creación), y `saldo_restante` parte del saldo de la tabla de amortización en ese punto, no del `valor_total` completo.
- Los conceptos recurrentes indefinidos (`gasto_fijo`/`ingreso` sin `duracion_meses`, deudas no amortizadas) se auto-extienden al año siguiente de forma perezosa: si al listar sus entradas no existe ninguna para el mes/año real de hoy, se generan automáticamente desde el mes actual hasta diciembre usando el monto de la entrada más reciente conocida — sin necesitar el gesto manual de editar enero. No hace nada si el concepto nunca tuvo ninguna entrada, ni si su entrada más reciente ya está en el futuro (evita rellenar con datos equivocados un concepto sembrado para un mes futuro).
- `deuda`/`gasto_fijo` pueden llevar `dia_vencimiento` (1-28, opcional, no aplica a `ingreso`) — a diferencia de los campos anteriores, es **siempre editable** porque es puramente informativo y no dispara ningún recálculo. Cada entrada mensual expone `vencida` (calculado al vuelo: no pagada y con fecha de vencimiento ya pasada).
- Login por email/password convive con Google: si alguien inicia sesión con Google usando un email que ya tiene cuenta por contraseña, el `google_sub` se **vincula automáticamente** a esa cuenta (el token de Google prueba que es dueño del correo). El registro por contraseña, en cambio, **siempre rechaza** un email ya usado (por Google o por otra contraseña) — nunca "reclama" una cuenta existente, porque no hay verificación de que el registrante sea el dueño real del correo. `/auth/register` y `/auth/login` tienen rate limiting en memoria (10 intentos / 5 min por IP); `/auth/google` no lo necesita porque ya depende de un token válido de Google. Sin verificación de email ni recuperación de contraseña por ahora (backlog futuro, diseñado para agregarse sin romper nada).
- Las categorías son una entidad real (`Categoria`), global por usuario (no separadas por tipo de concepto), asignables a un concepto en relación muchos-a-muchos (un concepto puede tener cero, una o varias). `POST /categorias` es **idempotente por nombre** (case-insensitive): pensado para que el frontend cree una categoría "al vuelo" sin verificar antes si ya existe. Renombrar o cambiarle el emoji a una categoría se refleja automáticamente en todo concepto que la use, porque el nombre/emoji viven en una sola fila, no duplicados. Eliminar una categoría la desasigna silenciosamente de sus conceptos (nunca bloquea el borrado ni deja un concepto en estado inválido). El emoji es opcional y debe ser uno de un set fijo curado de 16 (`ALLOWED_CATEGORIA_EMOJIS` en `app/models/categoria.py`) — cualquier otro valor se rechaza con 422. En `PATCH /concepts/{id}`, `categoria_ids` omitido significa "no tocar las categorías asignadas"; `categoria_ids: []` las vacía explícitamente — son solicitudes distintas.
- El backlog explícito está documentado en `openspec/changes/archive/2026-08-15-add-debt-amortization/proposal.md`: presupuesto por categorías tipo sobres (Necesidades/Deseos/Deudas/Futuro), función de importar datos, categorización de gastos por IA en lenguaje natural, multi-moneda. Reportes/agrupación por categoría (`Categoria`) quedan también como backlog futuro explícito — este cambio solo deja el modelo de datos listo para eso.
- `Tarea` es una entidad completamente independiente (sin FK hacia/desde `Concepto`, `Categoria`, ni ninguna otra tabla) — recordatorios/citas genéricos, no financieros. Usa su propio set fijo de emojis (`ALLOWED_TAREA_EMOJIS` en `app/models/tarea.py`, orientado a recordatorios: reloj, campana, teléfono, etc.), distinto al de categorías (`ALLOWED_CATEGORIA_EMOJIS`, orientado a finanzas). `vencida` se calcula al vuelo igual que `EntradaMensual.vencida` (fecha pasada + no completada), nunca se almacena. Deliberadamente **no** tiene ningún campo ni lógica de recurrencia/frecuencia — se pospuso hasta que exista una vista de calendario ("Agenda") donde tenga sentido mostrar instancias repetidas; no reintroducir sin revisar esa decisión primero.
- `Deudor` (dinero que otras personas le deben al usuario, inverso de `Concepto` tipo `deuda`) es también una entidad completamente independiente, sin relación con `Concepto`/`Categoria`/`Tarea`. Trackea pagos parciales vía `Abono` (FK `ondelete="CASCADE"`, sin `user_id` propio — la propiedad se valida siempre a través del `Deudor` padre, igual que `EntradaMensual` se valida a través de su `Concepto`). `saldo_restante` se calcula al vuelo igual que en `Concepto` (`monto_total` menos la suma de abonos), nunca se almacena. `garantia` es texto libre opcional (vacío = sin garantía, sin campo booleano separado). `activo` es un campo explícito para marcar un deudor como "terminado" sin borrar su historial de abonos. Las 3 tarjetas resumen de la pantalla de Deudores se calculan 100% en el frontend a partir de la lista, sin endpoint de resumen dedicado.
- `Gasto` (gasto variable/puntual, ej. "pizza $20.000") es una entidad standalone, distinta de `Concepto`: a diferencia del flujo mensual planeado (`EntradaMensual`), un gasto es un registro libre con su propio `monto`+`fecha`+`descripcion`, sin relación con ningún mes "planeado" de antemano. Puede llevar cero o varias `Categoria` asignadas vía una tabla de enlace propia (`GastoCategoria`, mismo patrón que `ConceptoCategoria` pero sin acoplar `Gasto` y `Concepto` entre sí) — reutiliza la misma entidad `Categoria` que ya usan los conceptos, sin un set de emojis propio. A diferencia de `Tarea`/`Deudor` (deliberadamente aislados del balance), `Gasto` sí impacta `GET /summary`: `monthly_summary` resta la suma de `Gasto.monto` cuyo `fecha` cae en el año/mes consultado (vía `EXTRACT(year/month FROM fecha)`, ya que a diferencia de `EntradaMensual` no tiene columnas `anio`/`mes` separadas) del `total_gastos`, usando siempre la fecha real del gasto y no la fecha en que se registró. Edición y eliminación son libres, sin ninguna restricción por fecha.
