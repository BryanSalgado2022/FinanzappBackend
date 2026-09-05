import enum
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel


class TipoAporte(str, enum.Enum):
    APORTE = "aporte"
    RETIRO = "retiro"


class AporteAhorro(SQLModel, table=True):
    __tablename__ = "aportes_ahorro"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    # Always stored positive - direction comes from tipo, not sign.
    monto: Decimal = Field(max_digits=14, decimal_places=2)
    tipo: TipoAporte
    fecha: date
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
