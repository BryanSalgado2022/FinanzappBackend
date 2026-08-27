from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.debts_summary import AnnualTrend
from app.schemas.summary import DisponibleRead, MonthlySummary
from app.services import debts_summary_service, summary_service

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("", response_model=MonthlySummary)
def get_monthly_summary(
    anio: int,
    mes: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MonthlySummary:
    return summary_service.monthly_summary(session, current_user.id, anio, mes)


@router.get("/annual", response_model=AnnualTrend)
def get_annual_trend(
    anio: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AnnualTrend:
    return debts_summary_service.annual_trend(session, current_user.id, anio)


@router.get("/disponible", response_model=DisponibleRead)
def get_disponible(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DisponibleRead:
    return DisponibleRead(
        disponible=summary_service.disponible(session, current_user),
        saldo_disponible_fecha=current_user.saldo_disponible_fecha,
    )
