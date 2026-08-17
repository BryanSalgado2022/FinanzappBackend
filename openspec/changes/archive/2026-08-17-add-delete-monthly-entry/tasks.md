## 1. Service layer

- [x] 1.1 Add `EntradaConVentanaFijaError` and `EntryNotFoundError` exception classes to `app/services/entry_service.py`
- [x] 1.2 Add `delete_entry(session, concepto, anio, mes)` per design.md

## 2. Router

- [x] 2.1 Add `DELETE /{anio}/{mes}` to `app/routers/entries.py`: validates `mes` range (1-12, same as PUT), fetches the concept (404 if missing), calls `delete_entry`, maps `EntradaConVentanaFijaError` → 409 and `EntryNotFoundError` → 404, returns 204 on success

## 3. Tests

- [x] 3.1 Test deleting an entry on an indefinite recurring concept succeeds and the month reports no entry afterward
- [x] 3.2 Test deleting rejects with 409 on a concept with amortization data
- [x] 3.3 Test deleting rejects with 409 on a concept with `duracion_meses` set
- [x] 3.4 Test deleting a non-existent entry returns 404
- [x] 3.5 Test deleting on a concept that doesn't belong to the user (or doesn't exist) returns 404
- [x] 3.6 Run the full test suite inside the `api` container and confirm all tests pass

## 4. Manual verification

- [x] 4.1 Restart the `api` container so the code changes take effect
- [x] 4.2 Verify via curl: create an indefinite recurring concept, add an entry, delete it, confirm it's gone via GET
- [x] 4.3 Verify via curl: attempt to delete an entry on an amortized debt, confirm 409
