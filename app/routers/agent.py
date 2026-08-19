from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.agent import ChatRequest, ChatResponse
from app.services import agent_service
from app.services.agent_service import GeminiUnavailableError
from app.services.rate_limit import check_rate_limit

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat")
def chat(
    payload: ChatRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    check_rate_limit(
        request, "agent_chat", limit=20, window_seconds=300, identifier=str(current_user.id)
    )
    try:
        return agent_service.chat(session, current_user, payload.messages, payload.current_date)
    except GeminiUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI agent is currently unavailable",
        ) from exc
