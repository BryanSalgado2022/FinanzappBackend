## Why

A user configured Disponible, then wanted to turn it off ("en caso de que no lo quiera poner"). There was no way to: `PATCH /users/me` with `saldo_disponible_inicial: null` cleared the value but always re-dated `saldo_disponible_fecha` to today regardless, so Disponible could never return to its "not configured" state — it would just keep computing from a zero baseline as of today instead of reporting `None`.

## What Changes

- Setting `saldo_disponible_inicial` to `null` now also clears `saldo_disponible_fecha` back to `null`, fully un-configuring Disponible. Setting it to a real value still re-dates `saldo_disponible_fecha` to today, unchanged.

## Capabilities

### Modified Capabilities
- `user-preferences`: "Setting the Disponible baseline always re-dates it to today" gains the clearing case.

## Impact

- `app/routers/users.py`: the `PATCH /users/me` handler's `saldo_disponible_fecha` assignment becomes conditional on whether the new `saldo_disponible_inicial` is `None`.
