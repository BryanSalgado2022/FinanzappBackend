from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class MonthlySummary(BaseModel):
    anio: int
    mes: int
    total_ingresos: Decimal
    total_gastos: Decimal
    balance_neto: Decimal


class DisponibleRead(BaseModel):
    # Both None together mean "never configured" - see openspec
    # add-available-balance. disponible is never zero-by-default; it's
    # simply absent until the user sets a starting figure.
    disponible: Decimal | None
    saldo_disponible_fecha: date | None
