from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.gasto import Gasto
from app.models.user import User
from app.schemas.categoria import CategoriaRead
from app.schemas.gasto import GastoCreate, GastoRead, GastoUpdate
from app.services import gasto_service
from app.services.gasto_service import GastoNotFoundError

router = APIRouter(prefix="/gastos", tags=["gastos"])


def _to_read(gasto: Gasto) -> GastoRead:
    return GastoRead(
        id=gasto.id,
        monto=gasto.monto,
        fecha=gasto.fecha,
        descripcion=gasto.descripcion,
        categorias=[CategoriaRead(id=c.id, nombre=c.nombre, emoji=c.emoji) for c in gasto.categorias],
        created_at=gasto.created_at,
    )


@router.post("", response_model=GastoRead, status_code=status.HTTP_201_CREATED)
def create_gasto(
    payload: GastoCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> GastoRead:
    try:
        gasto = gasto_service.create_gasto(
            session,
            current_user.id,
            payload.monto,
            payload.fecha,
            payload.descripcion,
            payload.categoria_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _to_read(gasto)


@router.get("", response_model=list[GastoRead])
def list_gastos(
    anio: int | None = None,
    mes: int | None = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[GastoRead]:
    gastos = gasto_service.list_gastos(session, current_user.id, anio=anio, mes=mes)
    return [_to_read(g) for g in gastos]


@router.get("/{gasto_id}", response_model=GastoRead)
def get_gasto(
    gasto_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> GastoRead:
    try:
        gasto = gasto_service.get_gasto(session, current_user.id, gasto_id)
    except GastoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found") from exc
    return _to_read(gasto)


@router.patch("/{gasto_id}", response_model=GastoRead)
def update_gasto(
    gasto_id: int,
    payload: GastoUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> GastoRead:
    try:
        gasto = gasto_service.update_gasto(
            session,
            current_user.id,
            gasto_id,
            monto=payload.monto,
            fecha=payload.fecha,
            descripcion=payload.descripcion,
            categoria_ids=payload.categoria_ids,
        )
    except GastoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _to_read(gasto)


@router.delete("/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gasto(
    gasto_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    try:
        gasto_service.delete_gasto(session, current_user.id, gasto_id)
    except GastoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found") from exc
