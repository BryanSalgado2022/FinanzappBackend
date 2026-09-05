from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.aporte_ahorro import AporteAhorro
from app.models.user import User
from app.schemas.ahorro import AporteAhorroCreate, AporteAhorroRead
from app.services import ahorro_service
from app.services.ahorro_service import AporteNotFoundError

router = APIRouter(prefix="/ahorros", tags=["ahorros"])


def _to_read(aporte: AporteAhorro) -> AporteAhorroRead:
    return AporteAhorroRead(
        id=aporte.id,
        monto=aporte.monto,
        fecha=aporte.fecha,
        tipo=aporte.tipo,
        created_at=aporte.created_at,
    )


@router.post("", response_model=AporteAhorroRead, status_code=status.HTTP_201_CREATED)
def create_aporte(
    payload: AporteAhorroCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AporteAhorroRead:
    aporte = ahorro_service.create_aporte(
        session, current_user.id, payload.monto, payload.fecha, payload.tipo
    )
    return _to_read(aporte)


@router.get("", response_model=list[AporteAhorroRead])
def list_aportes(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[AporteAhorroRead]:
    aportes = ahorro_service.list_aportes(session, current_user.id)
    return [_to_read(a) for a in aportes]


@router.delete("/{aporte_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_aporte(
    aporte_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    try:
        ahorro_service.delete_aporte(session, current_user.id, aporte_id)
    except AporteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aporte not found") from exc
