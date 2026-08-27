from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel


class Deudor(SQLModel, table=True):
    __tablename__ = "deudores"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    nombre: str
    monto_total: Decimal = Field(max_digits=14, decimal_places=2)
    fecha: date
    garantia: str | None = Field(default=None)
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
