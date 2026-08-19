from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.concepto import PeriodoTasa, TipoConcepto
from app.schemas.categoria import CategoriaRead


class ConceptoCreate(BaseModel):
    nombre: str
    tipo: TipoConcepto
    # Categories to assign at creation, by id - all must exist and belong to
    # the caller. Omitted or empty means no categories, same as today.
    categoria_ids: list[int] | None = None
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
    # Installment number to start generating entries from (optional,
    # amortization-only, immutable). For a debt already partway paid outside
    # the app - installments before this one are treated as already settled.
    cuota_inicial: int | None = Field(default=None, ge=1)
    # Fixed duration for gasto_fijo/ingreso recurrence (optional, immutable,
    # not valid on deuda). When set together with monto_planeado, generates
    # exactly that many months at creation instead of the open-ended behavior.
    duracion_meses: int | None = None
    # Day of month (1-28) an installment/payment is due (optional, any
    # concept type). Purely informational - editable at any time, see
    # ConceptoUpdate.
    dia_vencimiento: int | None = Field(default=None, ge=1, le=28)
    # Which year/month monto_planeado (and duracion_meses's window) should be
    # seeded into - defaults to the server's current year/month when omitted.
    # Lets the frontend create a concept for whatever month it's currently
    # viewing (e.g. a year-end bonus while browsing December) instead of
    # always landing in the real current month. Not used for amortized debts,
    # whose schedule is always anchored to the real creation date.
    anio: int | None = None
    mes: int | None = Field(default=None, ge=1, le=12)

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
    def validate_cuota_inicial(self) -> "ConceptoCreate":
        if self.cuota_inicial is None:
            return self
        if self.tasa_interes is None or self.numero_cuotas is None:
            raise ValueError("cuota_inicial requires tasa_interes and numero_cuotas to be set")
        if self.cuota_inicial > self.numero_cuotas:
            raise ValueError("cuota_inicial cannot be greater than numero_cuotas")
        return self


class ConceptoUpdate(BaseModel):
    nombre: str | None = None
    # None means "don't touch category assignments" (consistent with every
    # other field on this schema); an empty list explicitly clears them all -
    # these are different requests, see FinanzappBackend design.md.
    categoria_ids: list[int] | None = None
    activo: bool | None = None
    valor_total: Decimal | None = None
    dia_vencimiento: int | None = Field(default=None, ge=1, le=28)
    # Accepted only so it can be explicitly rejected with a clear message in
    # concept_service.update_concepto - cuota_inicial is always immutable.
    cuota_inicial: int | None = None


class ConceptoRead(BaseModel):
    id: int
    nombre: str
    tipo: TipoConcepto
    categorias: list[CategoriaRead]
    valor_total: Decimal | None
    saldo_restante: Decimal | None
    tasa_interes: Decimal | None
    periodo_tasa: PeriodoTasa | None
    numero_cuotas: int | None
    cuota_fija: Decimal | None
    cuota_inicial: int | None
    duracion_meses: int | None
    dia_vencimiento: int | None
    activo: bool
    finalizado_en: date | None
    created_at: datetime
