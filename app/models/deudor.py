from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.models.concepto import PeriodoTasa


class Deudor(SQLModel, table=True):
    __tablename__ = "deudores"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    nombre: str
    monto_total: Decimal = Field(max_digits=14, decimal_places=2)
    fecha: date
    garantia: str | None = Field(default=None)
    # Amortization terms (optional, immutable once both tasa_interes and
    # numero_cuotas are set - see debtor-management spec). When set, a full
    # CuotaDeudor schedule is generated instead of using free-form Abono.
    tasa_interes: Decimal | None = Field(default=None, max_digits=7, decimal_places=4)
    periodo_tasa: PeriodoTasa | None = Field(default=None)
    numero_cuotas: int | None = Field(default=None)
    # Installment number to start generating cuotas from (amortization only,
    # optional, immutable) - mirrors Concepto.cuota_inicial.
    cuota_inicial: int | None = Field(default=None)
    activo: bool = Field(default=True)
    # Set automatically to today's date when `activo` transitions to False,
    # cleared if reactivated - lets the Agenda calendar mark the exact day a
    # debtor was closed out. Never client-supplied - see design.md.
    finalizado_en: date | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Abono(SQLModel, table=True):
    __tablename__ = "abonos"

    id: int | None = Field(default=None, primary_key=True)
    deudor_id: int = Field(foreign_key="deudores.id", index=True, ondelete="CASCADE")
    monto: Decimal = Field(max_digits=14, decimal_places=2)
    fecha: date
    # How much of `monto` was interest rather than principal repayment -
    # excluded from the debtor's saldo_restante computation and counted
    # toward monthly income instead. None/0 means the payment is pure
    # principal, matching behavior before this field existed.
    interes: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CuotaDeudor(SQLModel, table=True):
    """One scheduled installment of an amortized debtor - mirrors
    EntradaMensual but keyed by deudor_id instead of concepto_id, plus an
    `interes` field EntradaMensual doesn't need (see design.md: only the
    interest portion of a received payment is income to the lender)."""

    __tablename__ = "cuotas_deudor"
    __table_args__ = (
        UniqueConstraint("deudor_id", "anio", "mes", name="uq_cuota_deudor_anio_mes"),
    )

    id: int | None = Field(default=None, primary_key=True)
    deudor_id: int = Field(foreign_key="deudores.id", index=True, ondelete="CASCADE")
    anio: int
    mes: int
    monto_planeado: Decimal = Field(max_digits=14, decimal_places=2)
    monto_pagado: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    pagado: bool = Field(default=False)
    # Set automatically to today's date the moment this cuota transitions to
    # pagado, cleared if marked unpaid again. Never client-supplied.
    fecha_pago: date | None = Field(default=None)
    # Planned interest component of this installment (from
    # amortization_service.generar_tabla_amortizacion at generation time) -
    # recognized as income only once pagado, keyed by fecha_pago (see
    # summary_service.py / design.md).
    interes: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
