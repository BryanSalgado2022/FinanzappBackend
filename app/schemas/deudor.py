from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DeudorCreate(BaseModel):
    nombre: str
    monto_total: Decimal
    fecha: date
    garantia: str | None = None


class DeudorUpdate(BaseModel):
    nombre: str | None = None
    monto_total: Decimal | None = None
    fecha: date | None = None
    garantia: str | None = None
    activo: bool | None = None


class DeudorRead(BaseModel):
    id: int
    nombre: str
    monto_total: Decimal
    fecha: date
    garantia: str | None
    activo: bool
    finalizado_en: date | None
    saldo_restante: Decimal


class AbonoCreate(BaseModel):
    monto: Decimal
    fecha: date


class AbonoRead(BaseModel):
    id: int
    monto: Decimal
    fecha: date
