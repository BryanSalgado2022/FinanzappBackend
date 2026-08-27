## 1. Service logic

- [x] 1.1 In `app/routers/users.py`'s `PATCH /users/me` handler, only re-date `saldo_disponible_fecha` to today when the new `saldo_disponible_inicial` is not `None`; clear it to `None` when the new value is `None`.

## 2. Tests

- [x] 2.1 Add a test in `tests/test_users.py`: setting `saldo_disponible_inicial` then clearing it to `null` results in both `saldo_disponible_inicial` and `saldo_disponible_fecha` being `null`.
- [x] 2.2 Add a test in `tests/test_disponible.py`: after clearing, `GET /summary/disponible` reports `disponible: null` again, not a zero-baseline figure.
- [x] 2.3 Run the full test suite and confirm it passes.
