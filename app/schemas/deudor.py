import enum
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.concepto import PeriodoTasa


class ModoAbonoCapital(str, enum.Enum):
    REDUCIR_PLAZO = "reducir_plazo"
    REDUCIR_CUOTA = "reducir_cuota"


class DeudorCreate(BaseModel):
    nombre: str
    monto_total: Decimal
    fecha: date
    garantia: str | None = None
    # Amortization terms (optional). tasa_interes and numero_cuotas must be
    # provided together. periodo_tasa defaults to "mensual" when omitted.
    tasa_interes: Decimal | None = None
    periodo_tasa: PeriodoTasa | None = None
    numero_cuotas: int | None = None
    # Installment number to start generating cuotas from (optional,
    # amortization-only, immutable) - mirrors ConceptoCreate.cuota_inicial.
    cuota_inicial: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_amortizacion(self) -> "DeudorCreate":
        tiene_tasa = self.tasa_interes is not None
        tiene_cuotas = self.numero_cuotas is not None
        if tiene_tasa != tiene_cuotas:
            raise ValueError("tasa_interes and numero_cuotas must be provided together")

        if tiene_tasa and self.periodo_tasa is None:
            self.periodo_tasa = PeriodoTasa.MENSUAL

        return self

    @model_validator(mode="after")
    def validate_cuota_inicial(self) -> "DeudorCreate":
        if self.cuota_inicial is None:
            return self
        if self.tasa_interes is None or self.numero_cuotas is None:
            raise ValueError("cuota_inicial requires tasa_interes and numero_cuotas to be set")
        if self.cuota_inicial > self.numero_cuotas:
            raise ValueError("cuota_inicial cannot be greater than numero_cuotas")
        return self


class DeudorUpdate(BaseModel):
    nombre: str | None = None
    monto_total: Decimal | None = None
    fecha: date | None = None
    garantia: str | None = None
    activo: bool | None = None


class DeudorAmortizacionUpdate(BaseModel):
    """Recalculates an already-amortized debtor's financial terms - see
    deudor_service.actualizar_amortizacion. All four fields are required
    together since recalculation always replaces the full term set;
    cuota_inicial is deliberately never part of this request."""

    monto_total: Decimal
    tasa_interes: Decimal
    periodo_tasa: PeriodoTasa
    numero_cuotas: int


class DeudorAmortizacionActivar(BaseModel):
    """Sets amortization terms for the first time on a debtor that doesn't
    yet have them - see deudor_service.activar_amortizacion. Distinct from
    DeudorAmortizacionUpdate: cuota_inicial IS accepted here (mirrors
    DeudorCreate, for a loan that predates the app)."""

    monto_total: Decimal
    tasa_interes: Decimal
    periodo_tasa: PeriodoTasa
    numero_cuotas: int
    cuota_inicial: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_cuota_inicial(self) -> "DeudorAmortizacionActivar":
        if self.cuota_inicial is not None and self.cuota_inicial > self.numero_cuotas:
            raise ValueError("cuota_inicial cannot be greater than numero_cuotas")
        return self


class DeudorRead(BaseModel):
    id: int
    nombre: str
    monto_total: Decimal
    fecha: date
    garantia: str | None
    tasa_interes: Decimal | None
    periodo_tasa: PeriodoTasa | None
    numero_cuotas: int | None
    cuota_fija: Decimal | None
    cuota_inicial: int | None
    activo: bool
    finalizado_en: date | None
    saldo_restante: Decimal


class CuotaDeudorRead(BaseModel):
    id: int
    deudor_id: int
    anio: int
    mes: int
    monto_planeado: Decimal
    monto_pagado: Decimal | None
    pagado: bool
    fecha_pago: date | None
    interes: Decimal | None


class CuotaDeudorUpdate(BaseModel):
    monto_pagado: Decimal | None = None
    pagado: bool = False
    # When set alongside a monto_pagado greater than monto_planeado, the
    # surplus is routed into a principal prepayment instead of being stored
    # against this cuota - see deudor_service.registrar_pago_con_sobrante
    # and design.md (add-abono-sobrante). None preserves today's behavior.
    abono_capital_modo: ModoAbonoCapital | None = None


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
    es_abono_capital: bool


class AbonoCapitalCreate(BaseModel):
    """Records an extraordinary principal prepayment against an amortized
    debtor - see deudor_service.registrar_abono_capital. Always pure
    principal (mirrors AbonoCreate but with no interes field at all, since
    an abono a capital is never partly interest by definition)."""

    monto: Decimal = Field(gt=0)
    fecha: date
    modo: ModoAbonoCapital
