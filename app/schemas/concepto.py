from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.concepto import PeriodoTasa, TipoConcepto


class ConceptoCreate(BaseModel):
    nombre: str
    tipo: TipoConcepto
    categoria: str | None = None
    valor_total: Decimal | None = None
    # Optional planned amount for the current month; for deuda/gasto_fijo concepts
    # this seeds the current month's entry and auto-generates the rest of the year.
    # Ignored (auto-generation instead follows the amortization schedule) when
    # tasa_interes/numero_cuotas are set.
    monto_planeado: Decimal | None = None
    # Amortization terms (deuda only, optional). tasa_interes and numero_cuotas
    # must be provided together. periodo_tasa defaults to "mensual" when omitted.
    tasa_interes: Decimal | None = None
    periodo_tasa: PeriodoTasa | None = None
    numero_cuotas: int | None = None
    # Fixed duration for gasto_fijo/ingreso recurrence (optional, immutable,
    # not valid on deuda). When set together with monto_planeado, generates
    # exactly that many months at creation instead of the open-ended behavior.
    duracion_meses: int | None = None
    # Day of month (1-28) an installment is due (optional, deuda/gasto_fijo
    # only). Purely informational - editable at any time, see ConceptoUpdate.
    dia_vencimiento: int | None = Field(default=None, ge=1, le=28)

    @model_validator(mode="after")
    def validate_valor_total(self) -> "ConceptoCreate":
        if self.valor_total is not None and self.tipo != TipoConcepto.DEUDA:
            raise ValueError("valor_total is only allowed for concepts of type 'deuda'")
        return self

    @model_validator(mode="after")
    def validate_amortizacion(self) -> "ConceptoCreate":
        if self.tipo != TipoConcepto.DEUDA and (
            self.tasa_interes is not None or self.numero_cuotas is not None
        ):
            raise ValueError("amortization fields are only allowed for concepts of type 'deuda'")

        tiene_tasa = self.tasa_interes is not None
        tiene_cuotas = self.numero_cuotas is not None
        if tiene_tasa != tiene_cuotas:
            raise ValueError("tasa_interes and numero_cuotas must be provided together")

        if tiene_tasa and self.periodo_tasa is None:
            self.periodo_tasa = PeriodoTasa.MENSUAL

        return self

    @model_validator(mode="after")
    def validate_duracion(self) -> "ConceptoCreate":
        if self.duracion_meses is not None and self.tipo == TipoConcepto.DEUDA:
            raise ValueError("duracion_meses is not allowed for concepts of type 'deuda'")
        return self

    @model_validator(mode="after")
    def validate_dia_vencimiento(self) -> "ConceptoCreate":
        if self.dia_vencimiento is not None and self.tipo == TipoConcepto.INGRESO:
            raise ValueError("dia_vencimiento is not allowed for concepts of type 'ingreso'")
        return self


class ConceptoUpdate(BaseModel):
    nombre: str | None = None
    categoria: str | None = None
    activo: bool | None = None
    valor_total: Decimal | None = None
    dia_vencimiento: int | None = Field(default=None, ge=1, le=28)


class ConceptoRead(BaseModel):
    id: int
    nombre: str
    tipo: TipoConcepto
    categoria: str | None
    valor_total: Decimal | None
    saldo_restante: Decimal | None
    tasa_interes: Decimal | None
    periodo_tasa: PeriodoTasa | None
    numero_cuotas: int | None
    cuota_fija: Decimal | None
    duracion_meses: int | None
    dia_vencimiento: int | None
    activo: bool
