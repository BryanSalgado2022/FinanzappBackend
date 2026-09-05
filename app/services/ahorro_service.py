from datetime import date
from decimal import Decimal

from sqlalchemy import case
from sqlmodel import Session, func, select

from app.models.aporte_ahorro import AporteAhorro, TipoAporte


class AporteNotFoundError(Exception):
    pass


def create_aporte(
    session: Session, user_id: int, monto: Decimal, fecha: date, tipo: TipoAporte
) -> AporteAhorro:
    aporte = AporteAhorro(user_id=user_id, monto=monto, fecha=fecha, tipo=tipo)
    session.add(aporte)
    session.commit()
    session.refresh(aporte)
    return aporte


def list_aportes(session: Session, user_id: int) -> list[AporteAhorro]:
    return list(
        session.exec(
            select(AporteAhorro)
            .where(AporteAhorro.user_id == user_id)
            .order_by(AporteAhorro.fecha.desc())
        )
    )


def delete_aporte(session: Session, user_id: int, aporte_id: int) -> None:
    aporte = session.get(AporteAhorro, aporte_id)
    if aporte is None or aporte.user_id != user_id:
        raise AporteNotFoundError(aporte_id)
    session.delete(aporte)
    session.commit()


def saldo_ahorros(session: Session, user_id: int) -> Decimal:
    signed = case(
        (AporteAhorro.tipo == TipoAporte.APORTE, AporteAhorro.monto),
        else_=-AporteAhorro.monto,
    )
    result = session.exec(
        select(func.coalesce(func.sum(signed), 0)).where(AporteAhorro.user_id == user_id)
    ).one()
    return Decimal(result)
