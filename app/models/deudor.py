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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Abono(SQLModel, table=True):
    __tablename__ = "abonos"

    id: int | None = Field(default=None, primary_key=True)
    deudor_id: int = Field(foreign_key="deudores.id", index=True, ondelete="CASCADE")
    monto: Decimal = Field(max_digits=14, decimal_places=2)
    fecha: date
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
