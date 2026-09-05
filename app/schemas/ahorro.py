from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.aporte_ahorro import TipoAporte


class AporteAhorroCreate(BaseModel):
    monto: Decimal
    fecha: date
    tipo: TipoAporte


class AporteAhorroRead(BaseModel):
    id: int
    monto: Decimal
    fecha: date
    tipo: TipoAporte
    created_at: datetime
