## 1. Implementation

- [x] 1.1 Add `created_at: datetime` to `ConceptoRead` in `app/schemas/concepto.py`
- [x] 1.2 Pass `created_at=concepto.created_at` in `_to_read` in `app/routers/concepts.py`

## 2. Verification

- [x] 2.1 Run the full test suite inside the `api` container and confirm all tests pass
- [x] 2.2 Verify via curl that `GET /concepts/{id}` includes `created_at`
