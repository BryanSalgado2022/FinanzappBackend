from decimal import Decimal

from pydantic import BaseModel


class EntradaMensualUpsert(BaseModel):
    monto_planeado: Decimal
    monto_pagado: Decimal | None = None
    pagado: bool = False


class EntradaMensualRead(BaseModel):
    id: int
    concepto_id: int
    anio: int
    mes: int
    monto_planeado: Decimal
    monto_pagado: Decimal | None
    pagado: bool
