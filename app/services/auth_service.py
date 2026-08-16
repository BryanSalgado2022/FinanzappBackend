from datetime import datetime, timedelta, timezone

import bcrypt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import jwt
from sqlmodel import Session, select

from app.config import get_settings
from app.models.user import User

settings = get_settings()


class InvalidGoogleTokenError(Exception):
    pass


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def verify_google_id_token(token: str) -> dict:
    try:
        return google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.google_client_id
        )
    except ValueError as exc:
        raise InvalidGoogleTokenError(str(exc)) from exc


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def get_or_create_user(session: Session, google_sub: str, email: str, name: str) -> User:
    user = session.exec(select(User).where(User.google_sub == google_sub)).first()
    if user is not None:
        return user

    # A password-only account may already own this email - Google's ID token
    # proves the requester owns it, so it's safe to link rather than reject
    # or create a duplicate (see openspec/changes/add-password-auth).
    user = session.exec(select(User).where(User.email == email)).first()
    if user is not None:
        user.google_sub = google_sub
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    user = User(google_sub=google_sub, email=email, name=name)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def register_user(session: Session, nombre: str, email: str, password: str) -> User:
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(name=nombre, email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate_with_password(session: Session, email: str, password: str) -> User:
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    return user


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {"sub": str(user.id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return int(payload["sub"])
