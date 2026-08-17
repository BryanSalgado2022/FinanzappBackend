import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel


class TipoConcepto(str, enum.Enum):
    DEUDA = "deuda"
    GASTO_FIJO = "gasto_fijo"
    INGRESO = "ingreso"


class PeriodoTasa(str, enum.Enum):
    MENSUAL = "mensual"
    ANUAL = "anual"


class Concepto(SQLModel, table=True):
    __tablename__ = "concepts"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    nombre: str
    tipo: TipoConcepto
    categoria: str | None = Field(default=None)
    valor_total: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    # Amortization terms (deuda only, optional, immutable once both tasa_interes
    # and numero_cuotas are set - see budget-concepts spec).
    tasa_interes: Decimal | None = Field(default=None, max_digits=7, decimal_places=4)
    periodo_tasa: PeriodoTasa | None = Field(default=None)
    numero_cuotas: int | None = Field(default=None)
    # Installment number to start generating entries from (amortization only,
    # optional, immutable) - for a debt the user already had before this app,
    # already paid up through cuota_inicial-1 outside the system.
    cuota_inicial: int | None = Field(default=None)
    # Fixed duration for gasto_fijo/ingreso recurrence (optional, immutable).
    # Not valid on deuda - see budget-concepts spec.
    duracion_meses: int | None = Field(default=None)
    # Day of month (1-28) a deuda/gasto_fijo installment is due (optional).
    # Purely informational/display - never feeds a calculation, so unlike the
    # fields above it stays mutable at any time - see budget-concepts spec.
    dia_vencimiento: int | None = Field(default=None)
    activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
