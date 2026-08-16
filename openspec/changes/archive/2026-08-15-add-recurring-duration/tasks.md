## 1. Data Model

- [x] 1.1 Add nullable `duracion_meses` (int) to the `Concepto` model
- [x] 1.2 Write and run an Alembic migration adding the column
- [x] 1.3 Update `ConceptoCreate` schema: accept `duracion_meses`, reject it on `deuda`

## 2. Generation Logic (spec: `monthly-budget`)

- [x] 2.1 Add `TipoConcepto.INGRESO` to `entry_service.RECURRING_TYPES`
- [x] 2.2 Implement `entry_service.generar_entradas_recurrentes` (fixed-count flat-amount generation, mirrors `generar_entradas_amortizacion`'s shape)
- [x] 2.3 Wire the three-way branch in `create_concept`: amortized debt → schedule, `duracion_meses` set → fixed-window, otherwise → existing open-ended path
- [x] 2.4 Write tests: creating a recurring `ingreso` without duration auto-generates through December (regression-style parity with `gasto_fijo`); creating with `duracion_meses` generates exactly that many months, including spanning into a future year; editing a month inside a fixed-duration window never generates entries beyond it

## 3. Wrap-up

- [x] 3.1 Run the full test suite and fix any failures
- [x] 3.2 Verify end-to-end locally via Docker Compose: create a recurring `ingreso` (no duration) and confirm it now behaves like `gasto_fijo`; create a `gasto_fijo` with `duracion_meses` and confirm it stops generating after that window
- [x] 3.3 Update the backend README
