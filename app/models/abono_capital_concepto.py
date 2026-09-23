from datetime import date
from decimal import Decimal

from sqlmodel import Field, SQLModel


class AbonoCapitalConcepto(SQLModel, table=True):
    """An extraordinary principal prepayment against an amortized debt
    concept - see concept_service.registrar_abono_capital. Unlike Deudor's
    Abono, this table is created solely for that feature and has no
    pre-existing rows, so every row here is by definition a capital
    prepayment - no es_abono_capital-style flag is needed (see design.md,
    add-abono-sobrante)."""

    __tablename__ = "abonos_capital_conceptos"

    id: int | None = Field(default=None, primary_key=True)
    concepto_id: int = Field(foreign_key="concepts.id", index=True, ondelete="CASCADE")
    monto: Decimal = Field(max_digits=14, decimal_places=2)
    fecha: date
