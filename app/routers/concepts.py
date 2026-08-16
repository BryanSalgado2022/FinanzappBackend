from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.concepto import Concepto, TipoConcepto
from app.models.user import User
from app.schemas.concepto import ConceptoCreate, ConceptoRead, ConceptoUpdate
from app.services import concept_service, entry_service
from app.services.concept_service import ConceptoNotFoundError

router = APIRouter(prefix="/concepts", tags=["concepts"])


def _to_read(session: Session, concepto: Concepto) -> ConceptoRead:
    return ConceptoRead(
        id=concepto.id,
        nombre=concepto.nombre,
        tipo=concepto.tipo,
        categoria=concepto.categoria,
        valor_total=concepto.valor_total,
        saldo_restante=concept_service.saldo_restante(session, concepto),
        activo=concepto.activo,
    )


@router.post("", response_model=ConceptoRead, status_code=status.HTTP_201_CREATED)
def create_concept(
    payload: ConceptoCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConceptoRead:
    concepto = concept_service.create_concepto(
        session,
        current_user.id,
        payload.nombre,
        payload.tipo,
        payload.categoria,
        payload.valor_total,
    )
    if payload.monto_planeado is not None and concepto.tipo in (
        TipoConcepto.DEUDA,
        TipoConcepto.GASTO_FIJO,
    ):
        today = date.today()
        entry_service.upsert_monthly_entry(
            session,
            concepto,
            today.year,
            today.month,
            monto_planeado=payload.monto_planeado,
        )
    return _to_read(session, concepto)


@router.get("", response_model=list[ConceptoRead])
def list_concepts(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ConceptoRead]:
    conceptos = concept_service.list_conceptos(session, current_user.id)
    return [_to_read(session, c) for c in conceptos]


@router.get("/{concepto_id}", response_model=ConceptoRead)
def get_concept(
    concepto_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConceptoRead:
    try:
        concepto = concept_service.get_concepto(session, current_user.id, concepto_id)
    except ConceptoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found") from exc
    return _to_read(session, concepto)


@router.patch("/{concepto_id}", response_model=ConceptoRead)
def update_concept(
    concepto_id: int,
    payload: ConceptoUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConceptoRead:
    try:
        concepto = concept_service.update_concepto(
            session,
            current_user.id,
            concepto_id,
            nombre=payload.nombre,
            categoria=payload.categoria,
            activo=payload.activo,
            valor_total=payload.valor_total,
        )
    except ConceptoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _to_read(session, concepto)


@router.delete("/{concepto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_concept(
    concepto_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    try:
        concept_service.delete_concepto(session, current_user.id, concepto_id)
    except ConceptoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found") from exc
