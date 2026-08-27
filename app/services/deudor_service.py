from datetime import date
from decimal import Decimal

from sqlmodel import Session, func, select

from app.models.deudor import Abono, Deudor


class DeudorNotFoundError(Exception):
    pass


class AbonoNotFoundError(Exception):
    pass


def create_deudor(
    session: Session,
    user_id: int,
    nombre: str,
    monto_total: Decimal,
    fecha: date,
    *,
    garantia: str | None = None,
) -> Deudor:
    deudor = Deudor(
        user_id=user_id,
        nombre=nombre,
        monto_total=monto_total,
        fecha=fecha,
        garantia=garantia,
    )
    session.add(deudor)
    session.commit()
    session.refresh(deudor)
    return deudor


def get_deudor(session: Session, user_id: int, deudor_id: int) -> Deudor:
    deudor = session.get(Deudor, deudor_id)
    if deudor is None or deudor.user_id != user_id:
        raise DeudorNotFoundError(deudor_id)
    return deudor


def list_deudores(session: Session, user_id: int) -> list[Deudor]:
    return list(session.exec(select(Deudor).where(Deudor.user_id == user_id)))


def update_deudor(
    session: Session,
    user_id: int,
    deudor_id: int,
    *,
    nombre: str | None = None,
    monto_total: Decimal | None = None,
    fecha: date | None = None,
    garantia: str | None = None,
    activo: bool | None = None,
) -> Deudor:
    deudor = get_deudor(session, user_id, deudor_id)
    if nombre is not None:
        deudor.nombre = nombre
    if monto_total is not None:
        deudor.monto_total = monto_total
    if fecha is not None:
        deudor.fecha = fecha
    if garantia is not None:
        deudor.garantia = garantia
    if activo is not None and activo != deudor.activo:
        # Only on an actual transition - see concept_service.update_concepto
        # for why re-sending the same value must not bump finalizado_en.
        deudor.finalizado_en = None if activo else date.today()
        deudor.activo = activo
    session.add(deudor)
    session.commit()
    session.refresh(deudor)
    return deudor


def delete_deudor(session: Session, user_id: int, deudor_id: int) -> None:
    deudor = get_deudor(session, user_id, deudor_id)
    session.delete(deudor)
    session.commit()


def saldo_restante(session: Session, deudor: Deudor) -> Decimal:
    # Only the principal portion of each abono (monto - interes) pays down
    # the loan - interest is income, not repayment, so it must not shrink
    # what's still owed. See openspec add-abono-interest.
    total_principal_abonado = session.exec(
        select(func.coalesce(func.sum(Abono.monto - func.coalesce(Abono.interes, 0)), 0)).where(
            Abono.deudor_id == deudor.id
        )
    ).one()
    return deudor.monto_total - Decimal(total_principal_abonado)


def create_abono(
    session: Session,
    user_id: int,
    deudor_id: int,
    monto: Decimal,
    fecha: date,
    *,
    interes: Decimal | None = None,
) -> Abono:
    deudor = get_deudor(session, user_id, deudor_id)
    abono = Abono(deudor_id=deudor.id, monto=monto, fecha=fecha, interes=interes)
    session.add(abono)
    session.commit()
    session.refresh(abono)
    return abono


def list_abonos(session: Session, user_id: int, deudor_id: int) -> list[Abono]:
    deudor = get_deudor(session, user_id, deudor_id)
    return list(session.exec(select(Abono).where(Abono.deudor_id == deudor.id)))


def delete_abono(session: Session, user_id: int, deudor_id: int, abono_id: int) -> None:
    deudor = get_deudor(session, user_id, deudor_id)
    abono = session.get(Abono, abono_id)
    if abono is None or abono.deudor_id != deudor.id:
        raise AbonoNotFoundError(abono_id)
    session.delete(abono)
    session.commit()
