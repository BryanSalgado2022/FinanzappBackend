from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

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
