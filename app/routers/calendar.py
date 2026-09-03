import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.calendar import IcsTokenRead
from app.services.ics_service import generate_ics

router = APIRouter(prefix="/calendar", tags=["calendar"])

ICS_MEDIA_TYPE = "text/calendar; charset=utf-8"


@router.get("/export")
def export_calendar(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    return Response(content=generate_ics(session, current_user), media_type=ICS_MEDIA_TYPE)


@router.post("/token", response_model=IcsTokenRead)
def create_or_regenerate_token(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> IcsTokenRead:
    current_user.ics_token = secrets.token_urlsafe(32)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return IcsTokenRead(ics_token=current_user.ics_token)


@router.get("/subscribe/{token}")
def subscribe_calendar(token: str, session: Session = Depends(get_session)) -> Response:
    user = session.exec(select(User).where(User.ics_token == token)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid calendar token")
    return Response(content=generate_ics(session, user), media_type=ICS_MEDIA_TYPE)
