from datetime import datetime, timedelta, timezone

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import jwt
from sqlmodel import Session, select

from app.config import get_settings
from app.models.user import User

settings = get_settings()


class InvalidGoogleTokenError(Exception):
    pass


def verify_google_id_token(token: str) -> dict:
    try:
        return google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.google_client_id
        )
    except ValueError as exc:
        raise InvalidGoogleTokenError(str(exc)) from exc


def get_or_create_user(session: Session, google_sub: str, email: str, name: str) -> User:
    user = session.exec(select(User).where(User.google_sub == google_sub)).first()
    if user is not None:
        return user
    user = User(google_sub=google_sub, email=email, name=name)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {"sub": str(user.id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return int(payload["sub"])
