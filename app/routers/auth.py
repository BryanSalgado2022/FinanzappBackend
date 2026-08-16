from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.config import get_settings
from app.database import get_session
from app.schemas.auth import GoogleSignInRequest, LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidGoogleTokenError,
    authenticate_with_password,
    create_access_token,
    get_or_create_user,
    register_user,
    verify_google_id_token,
)
from app.services.rate_limit import rate_limiter

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


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limiter("register"))],
)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> TokenResponse:
    try:
        user = register_user(session, payload.nombre, payload.email, payload.password)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from exc
    token = create_access_token(user)
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limiter("login"))],
)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    try:
        user = authenticate_with_password(session, payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        ) from exc
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
