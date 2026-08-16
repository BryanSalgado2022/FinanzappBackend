from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.summary import MonthlySummary
from app.services import summary_service

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("", response_model=MonthlySummary)
def get_monthly_summary(
    anio: int,
    mes: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MonthlySummary:
    return summary_service.monthly_summary(session, current_user.id, anio, mes)
