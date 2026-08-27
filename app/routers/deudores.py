from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.deudor import Abono, Deudor
from app.models.user import User
from app.schemas.deudor import AbonoCreate, AbonoRead, DeudorCreate, DeudorRead, DeudorUpdate
from app.services import deudor_service
from app.services.deudor_service import AbonoNotFoundError, DeudorNotFoundError

router = APIRouter(prefix="/deudores", tags=["deudores"])


def _to_read(session: Session, deudor: Deudor) -> DeudorRead:
    return DeudorRead(
        id=deudor.id,
        nombre=deudor.nombre,
        monto_total=deudor.monto_total,
        fecha=deudor.fecha,
        garantia=deudor.garantia,
        activo=deudor.activo,
        finalizado_en=deudor.finalizado_en,
        saldo_restante=deudor_service.saldo_restante(session, deudor),
    )


def _abono_to_read(abono: Abono) -> AbonoRead:
    return AbonoRead(id=abono.id, monto=abono.monto, fecha=abono.fecha, interes=abono.interes)


@router.post("", response_model=DeudorRead, status_code=status.HTTP_201_CREATED)
def create_deudor(
    payload: DeudorCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DeudorRead:
    deudor = deudor_service.create_deudor(
        session,
        current_user.id,
        payload.nombre,
        payload.monto_total,
        payload.fecha,
        garantia=payload.garantia,
    )
    return _to_read(session, deudor)


@router.get("", response_model=list[DeudorRead])
def list_deudores(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[DeudorRead]:
    deudores = deudor_service.list_deudores(session, current_user.id)
    return [_to_read(session, d) for d in deudores]


@router.get("/{deudor_id}", response_model=DeudorRead)
def get_deudor(
    deudor_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DeudorRead:
    try:
        deudor = deudor_service.get_deudor(session, current_user.id, deudor_id)
    except DeudorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debtor not found") from exc
    return _to_read(session, deudor)


@router.patch("/{deudor_id}", response_model=DeudorRead)
def update_deudor(
    deudor_id: int,
    payload: DeudorUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DeudorRead:
    try:
        deudor = deudor_service.update_deudor(
            session,
            current_user.id,
            deudor_id,
            nombre=payload.nombre,
            monto_total=payload.monto_total,
            fecha=payload.fecha,
            garantia=payload.garantia,
            activo=payload.activo,
        )
    except DeudorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debtor not found") from exc
    return _to_read(session, deudor)


@router.delete("/{deudor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deudor(
    deudor_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    try:
        deudor_service.delete_deudor(session, current_user.id, deudor_id)
    except DeudorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debtor not found") from exc


@router.post("/{deudor_id}/abonos", response_model=AbonoRead, status_code=status.HTTP_201_CREATED)
def create_abono(
    deudor_id: int,
    payload: AbonoCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AbonoRead:
    try:
        abono = deudor_service.create_abono(
            session, current_user.id, deudor_id, payload.monto, payload.fecha, interes=payload.interes
        )
    except DeudorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debtor not found") from exc
    return _abono_to_read(abono)


@router.get("/{deudor_id}/abonos", response_model=list[AbonoRead])
def list_abonos(
    deudor_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[AbonoRead]:
    try:
        abonos = deudor_service.list_abonos(session, current_user.id, deudor_id)
    except DeudorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debtor not found") from exc
    return [_abono_to_read(a) for a in abonos]


@router.delete("/{deudor_id}/abonos/{abono_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_abono(
    deudor_id: int,
    abono_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    try:
        deudor_service.delete_abono(session, current_user.id, deudor_id, abono_id)
    except DeudorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debtor not found") from exc
    except AbonoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Abono not found") from exc
