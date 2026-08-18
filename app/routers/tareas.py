from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.tarea import Tarea
from app.models.user import User
from app.schemas.tarea import TareaCreate, TareaRead, TareaUpdate
from app.services import tarea_service
from app.services.tarea_service import TareaNotFoundError

router = APIRouter(prefix="/tareas", tags=["tareas"])


def _to_read(tarea: Tarea) -> TareaRead:
    return TareaRead(
        id=tarea.id,
        titulo=tarea.titulo,
        emoji=tarea.emoji,
        fecha=tarea.fecha,
        hora=tarea.hora,
        nota=tarea.nota,
        completada=tarea.completada,
        vencida=tarea_service.es_vencida(tarea.fecha, tarea.completada),
    )


@router.post("", response_model=TareaRead, status_code=status.HTTP_201_CREATED)
def create_tarea(
    payload: TareaCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TareaRead:
    tarea = tarea_service.create_tarea(
        session,
        current_user.id,
        payload.titulo,
        emoji=payload.emoji,
        fecha=payload.fecha,
        hora=payload.hora,
        nota=payload.nota,
    )
    return _to_read(tarea)


@router.get("", response_model=list[TareaRead])
def list_tareas(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[TareaRead]:
    tareas = tarea_service.list_tareas(session, current_user.id)
    return [_to_read(t) for t in tareas]


@router.get("/{tarea_id}", response_model=TareaRead)
def get_tarea(
    tarea_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TareaRead:
    try:
        tarea = tarea_service.get_tarea(session, current_user.id, tarea_id)
    except TareaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found") from exc
    return _to_read(tarea)


@router.patch("/{tarea_id}", response_model=TareaRead)
def update_tarea(
    tarea_id: int,
    payload: TareaUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TareaRead:
    try:
        tarea = tarea_service.update_tarea(
            session,
            current_user.id,
            tarea_id,
            titulo=payload.titulo,
            emoji=payload.emoji,
            fecha=payload.fecha,
            hora=payload.hora,
            nota=payload.nota,
            completada=payload.completada,
        )
    except TareaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found") from exc
    return _to_read(tarea)


@router.delete("/{tarea_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tarea(
    tarea_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    try:
        tarea_service.delete_tarea(session, current_user.id, tarea_id)
    except TareaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found") from exc
