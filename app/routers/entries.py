from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.concepto import Concepto
from app.models.entrada_mensual import EntradaMensual
from app.models.user import User
from app.schemas.entrada_mensual import EntradaMensualRead, EntradaMensualUpsert
from app.services import concept_service, entry_service
from app.services.concept_service import ConceptoNotFoundError

router = APIRouter(prefix="/concepts/{concepto_id}/entries", tags=["entries"])


def _to_entry_read(concepto: Concepto, entry: EntradaMensual) -> EntradaMensualRead:
    return EntradaMensualRead(
        id=entry.id,
        concepto_id=entry.concepto_id,
        anio=entry.anio,
        mes=entry.mes,
        monto_planeado=entry.monto_planeado,
        monto_pagado=entry.monto_pagado,
        pagado=entry.pagado,
        vencida=entry_service.es_vencida(concepto.dia_vencimiento, entry.anio, entry.mes, entry.pagado),
    )


@router.get("", response_model=list[EntradaMensualRead])
def list_entries(
    concepto_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[EntradaMensualRead]:
    try:
        concepto = concept_service.get_concepto(session, current_user.id, concepto_id)
    except ConceptoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found") from exc
    entry_service.asegurar_entradas_anio_actual(session, concepto)
    entries = entry_service.list_entries(session, concepto_id)
    return [_to_entry_read(concepto, entry) for entry in entries]


@router.put("/{anio}/{mes}", response_model=EntradaMensualRead)
def upsert_entry(
    concepto_id: int,
    anio: int,
    mes: int,
    payload: EntradaMensualUpsert,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> EntradaMensualRead:
    if not 1 <= mes <= 12:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="mes must be 1-12")
    try:
        concepto = concept_service.get_concepto(session, current_user.id, concepto_id)
    except ConceptoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found") from exc

    entry = entry_service.upsert_monthly_entry(
        session,
        concepto,
        anio,
        mes,
        monto_planeado=payload.monto_planeado,
        monto_pagado=payload.monto_pagado,
        pagado=payload.pagado,
    )
    return _to_entry_read(concepto, entry)
