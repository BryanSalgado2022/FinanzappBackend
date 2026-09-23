from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.deudor import ModoAbonoCapital


class EntradaMensualUpsert(BaseModel):
    monto_planeado: Decimal
    monto_pagado: Decimal | None = None
    pagado: bool = False
    # When set alongside a monto_pagado greater than monto_planeado, the
    # surplus is routed into a principal prepayment instead of being stored
    # against this entry - see concept_service.registrar_abono_capital and
    # design.md (add-abono-sobrante). None preserves today's behavior exactly.
    abono_capital_modo: ModoAbonoCapital | None = None


class EntradaMensualRead(BaseModel):
    id: int
    concepto_id: int
    anio: int
    mes: int
    monto_planeado: Decimal
    monto_pagado: Decimal | None
    pagado: bool
    fecha_pago: date | None
    vencida: bool
