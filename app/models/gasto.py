from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Field, Relationship, SQLModel

from app.models.categoria import Categoria


class GastoCategoria(SQLModel, table=True):
    __tablename__ = "gasto_categoria"

    gasto_id: int = Field(foreign_key="gastos.id", primary_key=True, ondelete="CASCADE")
    categoria_id: int = Field(foreign_key="categorias.id", primary_key=True, ondelete="CASCADE")


class Gasto(SQLModel, table=True):
    __tablename__ = "gastos"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    monto: Decimal = Field(max_digits=14, decimal_places=2)
    fecha: date
    descripcion: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    categorias: list[Categoria] = Relationship(link_model=GastoCategoria)
