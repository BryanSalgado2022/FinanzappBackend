from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.categoria import Categoria
from app.models.user import User
from app.schemas.categoria import CategoriaCreate, CategoriaRead, CategoriaUpdate
from app.services import categoria_service
from app.services.categoria_service import CategoriaNotFoundError

router = APIRouter(prefix="/categorias", tags=["categorias"])


def _to_read(categoria: Categoria) -> CategoriaRead:
    return CategoriaRead(id=categoria.id, nombre=categoria.nombre, emoji=categoria.emoji)


@router.post("", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED)
def create_categoria(
    payload: CategoriaCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CategoriaRead:
    categoria = categoria_service.create_categoria(
        session, current_user.id, payload.nombre, payload.emoji
    )
    return _to_read(categoria)


@router.get("", response_model=list[CategoriaRead])
def list_categorias(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[CategoriaRead]:
    categorias = categoria_service.list_categorias(session, current_user.id)
    return [_to_read(c) for c in categorias]


@router.get("/{categoria_id}", response_model=CategoriaRead)
def get_categoria(
    categoria_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CategoriaRead:
    try:
        categoria = categoria_service.get_categoria(session, current_user.id, categoria_id)
    except CategoriaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from exc
    return _to_read(categoria)


@router.patch("/{categoria_id}", response_model=CategoriaRead)
def update_categoria(
    categoria_id: int,
    payload: CategoriaUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CategoriaRead:
    try:
        categoria = categoria_service.update_categoria(
            session,
            current_user.id,
            categoria_id,
            nombre=payload.nombre,
            emoji=payload.emoji,
        )
    except CategoriaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from exc
    return _to_read(categoria)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_categoria(
    categoria_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    try:
        categoria_service.delete_categoria(session, current_user.id, categoria_id)
    except CategoriaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from exc
