from datetime import date
from decimal import Decimal

from sqlalchemy import extract
from sqlmodel import Session, func, select

from app.models.categoria import Categoria
from app.models.gasto import Gasto


class GastoNotFoundError(Exception):
    pass


def _resolve_categorias(session: Session, user_id: int, categoria_ids: list[int]) -> list[Categoria]:
    if not categoria_ids:
        return []
    categorias = list(
        session.exec(
            select(Categoria).where(
                Categoria.user_id == user_id, Categoria.id.in_(categoria_ids)  # type: ignore[attr-defined]
            )
        )
    )
    found_ids = {c.id for c in categorias}
    missing = [cid for cid in categoria_ids if cid not in found_ids]
    if missing:
        raise ValueError(f"category ids not found for this user: {missing}")
    return categorias


def create_gasto(
    session: Session,
    user_id: int,
    monto: Decimal,
    fecha: date,
    descripcion: str,
    categoria_ids: list[int] | None,
) -> Gasto:
    gasto = Gasto(
        user_id=user_id,
        monto=monto,
        fecha=fecha,
        descripcion=descripcion,
        categorias=_resolve_categorias(session, user_id, categoria_ids or []),
    )
    session.add(gasto)
    session.commit()
    session.refresh(gasto)
    return gasto


def get_gasto(session: Session, user_id: int, gasto_id: int) -> Gasto:
    gasto = session.get(Gasto, gasto_id)
    if gasto is None or gasto.user_id != user_id:
        raise GastoNotFoundError(gasto_id)
    return gasto


def list_gastos(
    session: Session, user_id: int, *, anio: int | None = None, mes: int | None = None
) -> list[Gasto]:
    query = select(Gasto).where(Gasto.user_id == user_id)
    if anio is not None:
        query = query.where(extract("year", Gasto.fecha) == anio)
    if mes is not None:
        query = query.where(extract("month", Gasto.fecha) == mes)
    return list(session.exec(query))


def update_gasto(
    session: Session,
    user_id: int,
    gasto_id: int,
    *,
    monto: Decimal | None = None,
    fecha: date | None = None,
    descripcion: str | None = None,
    categoria_ids: list[int] | None = None,
) -> Gasto:
    gasto = get_gasto(session, user_id, gasto_id)
    if monto is not None:
        gasto.monto = monto
    if fecha is not None:
        gasto.fecha = fecha
    if descripcion is not None:
        gasto.descripcion = descripcion
    if categoria_ids is not None:
        # None means "don't touch"; an empty list explicitly clears every
        # assignment - same convention as Concepto's categoria_ids.
        gasto.categorias = _resolve_categorias(session, user_id, categoria_ids)
    session.add(gasto)
    session.commit()
    session.refresh(gasto)
    return gasto


def delete_gasto(session: Session, user_id: int, gasto_id: int) -> None:
    gasto = get_gasto(session, user_id, gasto_id)
    session.delete(gasto)
    session.commit()


def sum_gastos(session: Session, user_id: int, anio: int, mes: int) -> Decimal:
    result = session.exec(
        select(func.coalesce(func.sum(Gasto.monto), 0)).where(
            Gasto.user_id == user_id,
            extract("year", Gasto.fecha) == anio,
            extract("month", Gasto.fecha) == mes,
        )
    ).one()
    return Decimal(result)
