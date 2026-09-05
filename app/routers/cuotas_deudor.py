from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.deudor import CuotaDeudor
from app.models.user import User
from app.schemas.deudor import CuotaDeudorRead, CuotaDeudorUpdate
from app.services import cuota_deudor_service, deudor_service
from app.services.cuota_deudor_service import CuotaNotFoundError
from app.services.deudor_service import DeudorNotFoundError

router = APIRouter(prefix="/deudores/{deudor_id}/cuotas", tags=["cuotas-deudor"])


def _to_read(cuota: CuotaDeudor) -> CuotaDeudorRead:
    return CuotaDeudorRead(
        id=cuota.id,
        deudor_id=cuota.deudor_id,
        anio=cuota.anio,
        mes=cuota.mes,
        monto_planeado=cuota.monto_planeado,
        monto_pagado=cuota.monto_pagado,
        pagado=cuota.pagado,
        fecha_pago=cuota.fecha_pago,
        interes=cuota.interes,
    )


@router.get("", response_model=list[CuotaDeudorRead])
def list_cuotas(
    deudor_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[CuotaDeudorRead]:
    try:
        deudor_service.get_deudor(session, current_user.id, deudor_id)
    except DeudorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debtor not found") from exc
    cuotas = cuota_deudor_service.list_cuotas(session, deudor_id)
    return [_to_read(c) for c in cuotas]


@router.patch("/{anio}/{mes}", response_model=CuotaDeudorRead)
def mark_cuota(
    deudor_id: int,
    anio: int,
    mes: int,
    payload: CuotaDeudorUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CuotaDeudorRead:
    if not 1 <= mes <= 12:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="mes must be 1-12")
    try:
        deudor = deudor_service.get_deudor(session, current_user.id, deudor_id)
    except DeudorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debtor not found") from exc

    try:
        cuota = cuota_deudor_service.marcar_pagada(
            session, deudor, anio, mes, monto_pagado=payload.monto_pagado, pagado=payload.pagado
        )
    except CuotaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuota not found") from exc
    return _to_read(cuota)
