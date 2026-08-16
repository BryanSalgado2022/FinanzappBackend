from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.config import get_settings
from app.database import get_session
from app.schemas.auth import GoogleSignInRequest, TokenResponse
from app.services.auth_service import (
    InvalidGoogleTokenError,
    create_access_token,
    get_or_create_user,
    verify_google_id_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=TokenResponse)
def sign_in_with_google(
    payload: GoogleSignInRequest, session: Session = Depends(get_session)
) -> TokenResponse:
    try:
        claims = verify_google_id_token(payload.id_token)
    except InvalidGoogleTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token"
        ) from exc

    user = get_or_create_user(
        session,
        google_sub=claims["sub"],
        email=claims["email"],
        name=claims.get("name", claims["email"]),
    )
    token = create_access_token(user)
    return TokenResponse(access_token=token)


@router.post("/dev-login", response_model=TokenResponse)
def dev_login(session: Session = Depends(get_session)) -> TokenResponse:
    """Bypasses Google entirely and logs in as a fixed local user. Only exists
    when DEV_MODE=true - returns 404 otherwise so it's invisible outside local
    development (never enable this in a deployed environment)."""
    if not get_settings().dev_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    user = get_or_create_user(
        session,
        google_sub="dev-local-user",
        email="dev@localhost",
        name="Usuario de prueba",
    )
    token = create_access_token(user)
    return TokenResponse(access_token=token)
