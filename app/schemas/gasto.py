from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.categoria import CategoriaRead


class GastoCreate(BaseModel):
    monto: Decimal
    fecha: date
    descripcion: str
    # Categories to assign at creation, by id - all must exist and belong to
    # the caller. Omitted or empty means no categories.
    categoria_ids: list[int] | None = None


class GastoUpdate(BaseModel):
    monto: Decimal | None = None
    fecha: date | None = None
    descripcion: str | None = None
    # None means "don't touch category assignments"; an empty list explicitly
    # clears them all - same convention as ConceptoUpdate.categoria_ids.
    categoria_ids: list[int] | None = None


class GastoRead(BaseModel):
    id: int
    monto: Decimal
    fecha: date
    descripcion: str
    categorias: list[CategoriaRead]
    created_at: datetime
