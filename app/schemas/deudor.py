from datetime import date
from decimal import Decimal

from pydantic import BaseModel, model_validator


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
    interes: Decimal | None = None

    @model_validator(mode="after")
    def _interes_no_excede_monto(self) -> "AbonoCreate":
        if self.interes is not None and self.interes > self.monto:
            raise ValueError("interes no puede ser mayor que monto")
        return self


class AbonoRead(BaseModel):
    id: int
    monto: Decimal
    fecha: date
    interes: Decimal | None
