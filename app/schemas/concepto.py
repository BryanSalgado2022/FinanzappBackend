from decimal import Decimal

from pydantic import BaseModel, model_validator

from app.models.concepto import TipoConcepto


class ConceptoCreate(BaseModel):
    nombre: str
    tipo: TipoConcepto
    categoria: str | None = None
    valor_total: Decimal | None = None
    # Optional planned amount for the current month; for deuda/gasto_fijo concepts
    # this seeds the current month's entry and auto-generates the rest of the year.
    monto_planeado: Decimal | None = None

    @model_validator(mode="after")
    def validate_valor_total(self) -> "ConceptoCreate":
        if self.valor_total is not None and self.tipo != TipoConcepto.DEUDA:
            raise ValueError("valor_total is only allowed for concepts of type 'deuda'")
        return self


class ConceptoUpdate(BaseModel):
    nombre: str | None = None
    categoria: str | None = None
    activo: bool | None = None
    valor_total: Decimal | None = None


class ConceptoRead(BaseModel):
    id: int
    nombre: str
    tipo: TipoConcepto
    categoria: str | None
    valor_total: Decimal | None
    saldo_restante: Decimal | None
    activo: bool
