from decimal import Decimal

from pydantic import BaseModel


class DebtComposition(BaseModel):
    concepto_id: int
    nombre: str
    saldo_restante: Decimal


class DebtsSummary(BaseModel):
    numero_deudas: int
    total_adeudado: Decimal
    total_pagado: Decimal
    saldo_total_restante: Decimal
    progreso_porcentaje: Decimal
    composicion: list[DebtComposition]


class AnnualMonthTotal(BaseModel):
    mes: int
    total_ingresos: Decimal
    total_gastos: Decimal


class AnnualTrend(BaseModel):
    anio: int
    meses: list[AnnualMonthTotal]
