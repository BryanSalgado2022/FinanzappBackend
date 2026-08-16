import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel


class TipoConcepto(str, enum.Enum):
    DEUDA = "deuda"
    GASTO_FIJO = "gasto_fijo"
    INGRESO = "ingreso"


class Concepto(SQLModel, table=True):
    __tablename__ = "concepts"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    nombre: str
    tipo: TipoConcepto
    categoria: str | None = Field(default=None)
    valor_total: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
