from decimal import Decimal

from sqlmodel import Session, func, select

from app.models.concepto import Concepto, TipoConcepto
from app.models.entrada_mensual import EntradaMensual


class ConceptoNotFoundError(Exception):
    pass


def create_concepto(
    session: Session,
    user_id: int,
    nombre: str,
    tipo: TipoConcepto,
    categoria: str | None,
    valor_total: Decimal | None,
) -> Concepto:
    concepto = Concepto(
        user_id=user_id, nombre=nombre, tipo=tipo, categoria=categoria, valor_total=valor_total
    )
    session.add(concepto)
    session.commit()
    session.refresh(concepto)
    return concepto


def get_concepto(session: Session, user_id: int, concepto_id: int) -> Concepto:
    concepto = session.get(Concepto, concepto_id)
    if concepto is None or concepto.user_id != user_id:
        raise ConceptoNotFoundError(concepto_id)
    return concepto


def list_conceptos(session: Session, user_id: int) -> list[Concepto]:
    return list(session.exec(select(Concepto).where(Concepto.user_id == user_id)))


def update_concepto(
    session: Session,
    user_id: int,
    concepto_id: int,
    *,
    nombre: str | None = None,
    categoria: str | None = None,
    activo: bool | None = None,
    valor_total: Decimal | None = None,
) -> Concepto:
    concepto = get_concepto(session, user_id, concepto_id)
    if nombre is not None:
        concepto.nombre = nombre
    if categoria is not None:
        concepto.categoria = categoria
    if activo is not None:
        concepto.activo = activo
    if valor_total is not None:
        if concepto.tipo != TipoConcepto.DEUDA:
            raise ValueError("valor_total is only allowed for concepts of type 'deuda'")
        concepto.valor_total = valor_total
    session.add(concepto)
    session.commit()
    session.refresh(concepto)
    return concepto


def delete_concepto(session: Session, user_id: int, concepto_id: int) -> None:
    concepto = get_concepto(session, user_id, concepto_id)
    session.delete(concepto)
    session.commit()


def saldo_restante(session: Session, concepto: Concepto) -> Decimal | None:
    if concepto.tipo != TipoConcepto.DEUDA or concepto.valor_total is None:
        return None
    total_pagado = session.exec(
        select(func.coalesce(func.sum(EntradaMensual.monto_pagado), 0)).where(
            EntradaMensual.concepto_id == concepto.id
        )
    ).one()
    restante = concepto.valor_total - Decimal(total_pagado)
    return restante if restante > 0 else Decimal("0")
