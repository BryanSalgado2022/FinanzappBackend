from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _to_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        color_acento=user.color_acento,
        ahorros=user.ahorros,
    )


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return _to_read(current_user)


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserRead:
    # Each field must be distinguished as omitted (don't touch) vs
    # explicitly sent (set, possibly to null to clear) - checking the
    # deserialized value alone can't tell those apart. model_fields_set only
    # contains keys actually present in the request body.
    changed = False
    if "color_acento" in payload.model_fields_set:
        current_user.color_acento = payload.color_acento
        changed = True
    if "ahorros" in payload.model_fields_set:
        current_user.ahorros = payload.ahorros
        changed = True
    if changed:
        session.add(current_user)
        session.commit()
        session.refresh(current_user)
    return _to_read(current_user)
