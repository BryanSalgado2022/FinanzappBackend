from decimal import Decimal

from pydantic import BaseModel


class MonthlySummary(BaseModel):
    anio: int
    mes: int
    total_ingresos: Decimal
    total_gastos: Decimal
    balance_neto: Decimal
