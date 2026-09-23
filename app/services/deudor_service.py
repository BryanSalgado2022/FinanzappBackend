from datetime import date
from decimal import Decimal

from sqlmodel import Session, func, select

from app.models.concepto import PeriodoTasa
from app.models.deudor import Abono, CuotaDeudor, Deudor
from app.services import cuota_deudor_service
from app.services.amortization_service import (
    calcular_cuota_fija,
    calcular_cuotas_restantes,
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
        # Principal prepayments recorded via registrar_abono_capital also
        # reduce the balance - gated on es_abono_capital specifically (not
        # every Abono) so that any abono recorded BEFORE the debtor was
        # amortized stays pure history, per add-activate-amortization.
        total_abonos_capital = session.exec(
            select(func.coalesce(func.sum(Abono.monto), 0)).where(
                Abono.deudor_id == deudor.id, Abono.es_abono_capital.is_(True)
            )
        ).one()
        restante = monto_total_efectivo(deudor) - Decimal(total_pagado) - Decimal(total_abonos_capital)
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


def cuota_fija(session: Session, deudor: Deudor) -> Decimal | None:
    """Reads the fixed installment from the actual schedule (the next
    not-yet-paid cuota's planned amount) rather than recomputing it from
    stored terms - see design.md (add-abono-capital): a principal
    prepayment can change the remaining schedule without touching
    monto_total/numero_cuotas, which stay as historical record of the
    original loan. Falls back to the most recent cuota if none are unpaid,
    or the stored-terms computation if no schedule exists at all yet."""
    if not es_amortizado(deudor):
        return None
    proxima = session.exec(
        select(CuotaDeudor)
        .where(CuotaDeudor.deudor_id == deudor.id, CuotaDeudor.pagado.is_(False))
        .order_by(CuotaDeudor.anio, CuotaDeudor.mes)
    ).first()
    if proxima is not None:
        return proxima.monto_planeado
    ultima = session.exec(
        select(CuotaDeudor)
        .where(CuotaDeudor.deudor_id == deudor.id)
        .order_by(CuotaDeudor.anio.desc(), CuotaDeudor.mes.desc())
    ).first()
    if ultima is not None:
        return ultima.monto_planeado
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


def activar_amortizacion(
    session: Session,
    user_id: int,
    deudor_id: int,
    *,
    monto_total: Decimal,
    tasa_interes: Decimal,
    periodo_tasa: PeriodoTasa,
    numero_cuotas: int,
    cuota_inicial: int | None,
) -> tuple[Deudor, int, int]:
    """Sets amortization terms for the first time on a debtor that doesn't
    yet have them. Unlike actualizar_amortizacion, this behaves like fresh
    creation math-wise: anchored at today, cuota_inicial comes purely from
    the caller (not derived from paid-cuota count) - see design.md. Every
    not-yet-paid cuota is deleted; existing abonos are left untouched as
    historical record and no longer feed saldo_restante once amortized.
    Returns (deudor, anio_inicio, mes_inicio) for the router to pass into
    cuota_deudor_service.generar_cuotas_amortizacion."""
    deudor = get_deudor(session, user_id, deudor_id)
    if es_amortizado(deudor):
        raise ValueError(
            "this debtor already has amortization terms; use the correction "
            "endpoint instead"
        )

    cuotas = list(session.exec(select(CuotaDeudor).where(CuotaDeudor.deudor_id == deudor.id)))
    for cuota in cuotas:
        if not cuota.pagado:
            session.delete(cuota)

    deudor.monto_total = monto_total
    deudor.tasa_interes = tasa_interes
    deudor.periodo_tasa = periodo_tasa
    deudor.numero_cuotas = numero_cuotas
    deudor.cuota_inicial = cuota_inicial
    session.add(deudor)
    session.commit()
    session.refresh(deudor)

    hoy = date.today()
    return deudor, hoy.year, hoy.month


def registrar_abono_capital(
    session: Session,
    user_id: int,
    deudor_id: int,
    *,
    monto: Decimal,
    fecha: date,
    modo: str,
) -> Deudor:
    """Records an extraordinary principal prepayment against an amortized
    debtor - see design.md (add-abono-capital). monto_total/numero_cuotas
    stay as historical record of the original loan (only numero_cuotas is
    bumped to reflect the new total installment count); the reduction is
    tracked via an Abono row instead, which saldo_restante now also
    subtracts. Fully settling the balance closes the debtor, mirroring the
    existing activo/finalizado_en transition."""
    deudor = get_deudor(session, user_id, deudor_id)
    if not es_amortizado(deudor):
        raise ValueError(
            "principal prepayments only apply to amortized debtors; use a "
            "regular abono instead"
        )

    abono = Abono(deudor_id=deudor.id, monto=monto, fecha=fecha, interes=None, es_abono_capital=True)
    session.add(abono)
    session.commit()

    nuevo_saldo = saldo_restante(session, deudor)

    cuotas = list(session.exec(select(CuotaDeudor).where(CuotaDeudor.deudor_id == deudor.id)))

    if nuevo_saldo <= 0:
        for cuota in cuotas:
            if not cuota.pagado:
                session.delete(cuota)
        if deudor.activo:
            deudor.activo = False
            deudor.finalizado_en = date.today()
            session.add(deudor)
        session.commit()
        session.refresh(deudor)
        return deudor

    pagadas = [c for c in cuotas if c.pagado]
    n_pagadas = len(pagadas)
    siguiente_numero = (deudor.cuota_inicial or 1) + n_pagadas

    if pagadas:
        anio_ultimo, mes_ultimo = max((c.anio, c.mes) for c in pagadas)
        anio_inicio, mes_inicio = _sumar_un_mes(anio_ultimo, mes_ultimo)
    else:
        hoy = date.today()
        anio_inicio, mes_inicio = hoy.year, hoy.month

    tasa_mensual = tasa_mensual_desde(deudor.tasa_interes, deudor.periodo_tasa)
    cuota_fija_actual = cuota_fija(session, deudor)

    if modo == "reducir_cuota":
        numero_cuotas_restantes = deudor.numero_cuotas - siguiente_numero + 1
    elif modo == "reducir_plazo":
        numero_cuotas_restantes = calcular_cuotas_restantes(nuevo_saldo, tasa_mensual, cuota_fija_actual)
    else:
        raise ValueError("modo must be 'reducir_plazo' or 'reducir_cuota'")

    if numero_cuotas_restantes <= 0:
        raise ValueError("this debtor's schedule has no remaining installments to adjust")

    for cuota in cuotas:
        if not cuota.pagado:
            session.delete(cuota)

    deudor.numero_cuotas = (siguiente_numero - 1) + numero_cuotas_restantes
    session.add(deudor)
    session.commit()
    session.refresh(deudor)

    tabla = generar_tabla_amortizacion(nuevo_saldo, tasa_mensual, numero_cuotas_restantes)
    cuota_deudor_service.generar_cuotas_amortizacion(
        session, deudor, tabla, anio_inicio, mes_inicio, cuota_inicial=1
    )
    return deudor


def registrar_pago_con_sobrante(
    session: Session,
    user_id: int,
    deudor_id: int,
    *,
    anio: int,
    mes: int,
    monto_pagado: Decimal,
    modo: str,
) -> CuotaDeudor:
    """Marks a cuota paid, capping its stored monto_pagado to monto_planeado,
    and routes the surplus into a principal prepayment via
    registrar_abono_capital - all in one call, so saldo_restante never
    double-counts the surplus (see design.md, add-abono-sobrante). Rejects
    if the debtor isn't amortized or if monto_pagado doesn't exceed the
    cuota's monto_planeado (nothing to route)."""
    deudor = get_deudor(session, user_id, deudor_id)
    if not es_amortizado(deudor):
        raise ValueError(
            "routing a payment surplus into a principal prepayment only "
            "applies to amortized debtors"
        )

    cuota = cuota_deudor_service.get_cuota(session, deudor_id, anio, mes)
    if cuota is None:
        raise cuota_deudor_service.CuotaNotFoundError()
    if monto_pagado <= cuota.monto_planeado:
        raise ValueError("no hay sobrante que registrar como abono a capital")

    cuota = cuota_deudor_service.marcar_pagada(
        session, deudor, anio, mes, monto_pagado=cuota.monto_planeado, pagado=True
    )
    excedente = monto_pagado - cuota.monto_planeado
    registrar_abono_capital(
        session, user_id, deudor_id, monto=excedente, fecha=cuota.fecha_pago, modo=modo
    )
    session.refresh(cuota)
    return cuota


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
