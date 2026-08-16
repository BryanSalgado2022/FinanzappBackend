from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.debts_summary import DebtsSummary
from app.services import debts_summary_service

router = APIRouter(prefix="/debts", tags=["debts"])


@router.get("/summary", response_model=DebtsSummary)
def get_debts_summary(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DebtsSummary:
    return debts_summary_service.debts_summary(session, current_user.id)
