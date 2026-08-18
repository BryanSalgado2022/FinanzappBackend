from sqlmodel import Session, func, select

from app.models.categoria import Categoria


class CategoriaNotFoundError(Exception):
    pass


def create_categoria(session: Session, user_id: int, nombre: str, emoji: str | None) -> Categoria:
    """Find-or-create by nombre (case-insensitive), scoped to the user - lets
    the frontend's inline "type a new name to create it" flow call this
    unconditionally without a separate existence check, and guarantees no two
    categories differing only by case for the same user."""
    existing = session.exec(
        select(Categoria).where(
            Categoria.user_id == user_id,
            func.lower(Categoria.nombre) == nombre.lower(),
        )
    ).first()
    if existing is not None:
        return existing

    categoria = Categoria(user_id=user_id, nombre=nombre, emoji=emoji)
    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    return categoria


def get_categoria(session: Session, user_id: int, categoria_id: int) -> Categoria:
    categoria = session.get(Categoria, categoria_id)
    if categoria is None or categoria.user_id != user_id:
        raise CategoriaNotFoundError(categoria_id)
    return categoria


def list_categorias(session: Session, user_id: int) -> list[Categoria]:
    return list(session.exec(select(Categoria).where(Categoria.user_id == user_id)))


def update_categoria(
    session: Session,
    user_id: int,
    categoria_id: int,
    *,
    nombre: str | None = None,
    emoji: str | None = None,
) -> Categoria:
    categoria = get_categoria(session, user_id, categoria_id)
    if nombre is not None:
        categoria.nombre = nombre
    if emoji is not None:
        categoria.emoji = emoji
    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    return categoria


def delete_categoria(session: Session, user_id: int, categoria_id: int) -> None:
    categoria = get_categoria(session, user_id, categoria_id)
    session.delete(categoria)
    session.commit()
