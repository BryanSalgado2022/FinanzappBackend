from datetime import date
from decimal import Decimal

from sqlmodel import Session, func, select

from app.models.concepto import PeriodoTasa
from app.models.deudor import Abono, CuotaDeudor, Deudor
from app.services import cuota_deudor_service
from app.services.amortization_service import (
    calcular_cuota_fija,
    generar_tabla_amortizacion,
    tasa_mensual_desde,
)


class DeudorNotFoundError(Exception):
    pass


class AbonoNotFoundError(Exception):
    pass


def es_amortizado(deudor: Deudor) -> bool:
    return deudor.tasa_interes is not None and deudor.numero_cuotas is not None


def create_deudor(
    session: Session,
    user_id: int,
    nombre: str,
    monto_total: Decimal,
    fecha: date,
    *,
    garantia: str | None = None,
    tasa_interes: Decimal | None = None,
    periodo_tasa: PeriodoTasa | None = None,
    numero_cuotas: int | None = None,
    cuota_inicial: int | None = None,
) -> Deudor:
    deudor = Deudor(
        user_id=user_id,
        nombre=nombre,
        monto_total=monto_total,
        fecha=fecha,
        garantia=garantia,
        tasa_interes=tasa_interes,
        periodo_tasa=periodo_tasa,
        numero_cuotas=numero_cuotas,
        cuota_inicial=cuota_inicial,
    )
    session.add(deudor)
    session.commit()
    session.refresh(deudor)

    if es_amortizado(deudor):
        tasa_mensual = tasa_mensual_desde(deudor.tasa_interes, deudor.periodo_tasa)
        tabla = generar_tabla_amortizacion(deudor.monto_total, tasa_mensual, deudor.numero_cuotas)
        cuota_deudor_service.generar_cuotas_amortizacion(
            session,
            deudor,
            tabla,
            deudor.fecha.year,
            deudor.fecha.month,
            cuota_inicial=deudor.cuota_inicial or 1,
        )

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


def monto_total_efectivo(deudor: Deudor) -> Decimal:
    """The debtor's starting amount for saldo_restante purposes -
    monto_total, unless cuota_inicial skips past some installments, in which
    case it's the schedule's balance right after the installment before
    cuota_inicial (those earlier installments never have cuotas or
    monto_pagado in this system). Mirrors concept_service.valor_total_efectivo."""
    if not deudor.cuota_inicial or deudor.cuota_inicial <= 1 or not es_amortizado(deudor):
        return deudor.monto_total
    tasa_mensual = tasa_mensual_desde(deudor.tasa_interes, deudor.periodo_tasa)
    tabla = generar_tabla_amortizacion(deudor.monto_total, tasa_mensual, deudor.numero_cuotas)
    return tabla[deudor.cuota_inicial - 2]["saldo"]


def saldo_restante(session: Session, deudor: Deudor) -> Decimal:
    if es_amortizado(deudor):
        total_pagado = session.exec(
            select(func.coalesce(func.sum(CuotaDeudor.monto_pagado), 0)).where(
                CuotaDeudor.deudor_id == deudor.id
            )
        ).one()
        restante = monto_total_efectivo(deudor) - Decimal(total_pagado)
        return restante if restante > 0 else Decimal("0")

    # Only the principal portion of each abono (monto - interes) pays down
    # the loan - interest is income, not repayment, so it must not shrink
    # what's still owed. See openspec add-abono-interest.
    total_principal_abonado = session.exec(
        select(func.coalesce(func.sum(Abono.monto - func.coalesce(Abono.interes, 0)), 0)).where(
            Abono.deudor_id == deudor.id
        )
    ).one()
    return deudor.monto_total - Decimal(total_principal_abonado)


def cuota_fija(deudor: Deudor) -> Decimal | None:
    if not es_amortizado(deudor):
        return None
    tasa_mensual = tasa_mensual_desde(deudor.tasa_interes, deudor.periodo_tasa)
    return calcular_cuota_fija(deudor.monto_total, tasa_mensual, deudor.numero_cuotas)


def _sumar_un_mes(anio: int, mes: int) -> tuple[int, int]:
    total = (anio * 12 + (mes - 1)) + 1
    return total // 12, total % 12 + 1


def actualizar_amortizacion(
    session: Session,
    user_id: int,
    deudor_id: int,
    *,
    monto_total: Decimal,
    tasa_interes: Decimal,
    periodo_tasa: PeriodoTasa,
    numero_cuotas: int,
) -> tuple[Deudor, int, int, int]:
    """Corrects an already-amortized debtor's financial terms. Every paid
    cuota is left completely untouched; every unpaid cuota is deleted so the
    caller can regenerate the remaining schedule from the returned anchor -
    mirrors concept_service.actualizar_amortizacion exactly. Returns
    (deudor, anio_inicio, mes_inicio, siguiente_numero) for the router to
    pass into cuota_deudor_service.generar_cuotas_amortizacion."""
    deudor = get_deudor(session, user_id, deudor_id)
    if not es_amortizado(deudor):
        raise ValueError(
            "this debtor has no existing amortization terms to correct; "
            "amortization can only be set at creation"
        )

    cuotas = list(session.exec(select(CuotaDeudor).where(CuotaDeudor.deudor_id == deudor.id)))
    pagadas = [c for c in cuotas if c.pagado]
    n_pagadas = len(pagadas)
    siguiente_numero = (deudor.cuota_inicial or 1) + n_pagadas

    if numero_cuotas < siguiente_numero - 1:
        raise ValueError(
            "numero_cuotas cannot be less than the installments already paid on this debtor"
        )

    if pagadas:
        anio_ultimo, mes_ultimo = max((c.anio, c.mes) for c in pagadas)
        anio_inicio, mes_inicio = _sumar_un_mes(anio_ultimo, mes_ultimo)
    else:
        hoy = date.today()
        anio_inicio, mes_inicio = hoy.year, hoy.month

    for cuota in cuotas:
        if not cuota.pagado:
            session.delete(cuota)

    deudor.monto_total = monto_total
    deudor.tasa_interes = tasa_interes
    deudor.periodo_tasa = periodo_tasa
    deudor.numero_cuotas = numero_cuotas
    session.add(deudor)
    session.commit()
    session.refresh(deudor)

    return deudor, anio_inicio, mes_inicio, siguiente_numero


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
    if es_amortizado(deudor):
        raise ValueError(
            "this debtor is amortized and tracks payments through its installment "
            "schedule instead of free-form abonos"
        )
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
