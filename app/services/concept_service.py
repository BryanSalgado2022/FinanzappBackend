from datetime import date
from decimal import Decimal

from sqlmodel import Session, func, select

from app.models.abono_capital_concepto import AbonoCapitalConcepto
from app.models.categoria import Categoria
from app.models.concepto import Concepto, PeriodoTasa, TipoConcepto
from app.models.entrada_mensual import EntradaMensual
from app.services import entry_service
from app.services.amortization_service import (
    calcular_cuota_fija,
    calcular_cuotas_restantes,
    generar_tabla_amortizacion,
    tasa_mensual_desde,
)


class ConceptoNotFoundError(Exception):
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


def create_concepto(
    session: Session,
    user_id: int,
    nombre: str,
    tipo: TipoConcepto,
    categoria_ids: list[int] | None,
    valor_total: Decimal | None,
    *,
    tasa_interes: Decimal | None = None,
    periodo_tasa: PeriodoTasa | None = None,
    numero_cuotas: int | None = None,
    cuota_inicial: int | None = None,
    duracion_meses: int | None = None,
    dia_vencimiento: int | None = None,
) -> Concepto:
    concepto = Concepto(
        user_id=user_id,
        nombre=nombre,
        tipo=tipo,
        categorias=_resolve_categorias(session, user_id, categoria_ids or []),
        valor_total=valor_total,
        tasa_interes=tasa_interes,
        periodo_tasa=periodo_tasa,
        numero_cuotas=numero_cuotas,
        cuota_inicial=cuota_inicial,
        duracion_meses=duracion_meses,
        dia_vencimiento=dia_vencimiento,
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


def es_amortizada(concepto: Concepto) -> bool:
    return concepto.tasa_interes is not None and concepto.numero_cuotas is not None


def update_concepto(
    session: Session,
    user_id: int,
    concepto_id: int,
    *,
    nombre: str | None = None,
    categoria_ids: list[int] | None = None,
    activo: bool | None = None,
    valor_total: Decimal | None = None,
    dia_vencimiento: int | None = None,
    cuota_inicial: int | None = None,
) -> Concepto:
    concepto = get_concepto(session, user_id, concepto_id)
    if nombre is not None:
        concepto.nombre = nombre
    if categoria_ids is not None:
        # None means "don't touch"; an empty list explicitly clears every
        # assignment - see ConceptoUpdate's categoria_ids docstring.
        concepto.categorias = _resolve_categorias(session, user_id, categoria_ids)
    if activo is not None and activo != concepto.activo:
        # Only on an actual transition, not every save where activo happens
        # to be re-sent with its current value - otherwise finalizado_en
        # would get bumped to today on every unrelated edit.
        concepto.finalizado_en = None if activo else date.today()
        concepto.activo = activo
    if cuota_inicial is not None:
        raise ValueError(
            "cuota_inicial cannot be changed after creation; "
            "delete this concept and create a new one instead"
        )
    if valor_total is not None:
        if concepto.tipo != TipoConcepto.DEUDA:
            raise ValueError("valor_total is only allowed for concepts of type 'deuda'")
        if es_amortizada(concepto):
            raise ValueError(
                "valor_total cannot be changed on a debt with amortization data; "
                "delete this concept and create a new one instead"
            )
        concepto.valor_total = valor_total
    if dia_vencimiento is not None:
        # No es_amortizada guard here, unlike valor_total above - dia_vencimiento
        # is informational only and never feeds a recalculation, so it stays
        # editable even on a locked amortized debt.
        concepto.dia_vencimiento = dia_vencimiento
    session.add(concepto)
    session.commit()
    session.refresh(concepto)
    return concepto


def _sumar_un_mes(anio: int, mes: int) -> tuple[int, int]:
    total = (anio * 12 + (mes - 1)) + 1
    return total // 12, total % 12 + 1


def actualizar_amortizacion(
    session: Session,
    user_id: int,
    concepto_id: int,
    *,
    valor_total: Decimal,
    tasa_interes: Decimal,
    periodo_tasa: PeriodoTasa,
    numero_cuotas: int,
) -> tuple[Concepto, int, int, int]:
    """Corrects an already-amortized debt's financial terms. Every paid entry
    is left completely untouched; every unpaid entry is deleted so the
    caller can regenerate the remaining schedule from the returned anchor -
    see design.md for the full algorithm. Returns
    (concepto, anio_inicio, mes_inicio, siguiente_numero) for the router to
    pass into entry_service.generar_entradas_amortizacion."""
    concepto = get_concepto(session, user_id, concepto_id)
    if concepto.tipo != TipoConcepto.DEUDA:
        raise ValueError("amortization terms only apply to concepts of type 'deuda'")
    if not es_amortizada(concepto):
        raise ValueError(
            "this concept has no existing amortization terms to correct; "
            "amortization can only be set at creation"
        )

    entradas = list(
        session.exec(select(EntradaMensual).where(EntradaMensual.concepto_id == concepto.id))
    )
    pagadas = [e for e in entradas if e.pagado]
    n_pagadas = len(pagadas)
    siguiente_numero = (concepto.cuota_inicial or 1) + n_pagadas

    if numero_cuotas < siguiente_numero - 1:
        raise ValueError(
            "numero_cuotas cannot be less than the installments already paid on this debt"
        )

    if pagadas:
        anio_ultimo, mes_ultimo = max((e.anio, e.mes) for e in pagadas)
        anio_inicio, mes_inicio = _sumar_un_mes(anio_ultimo, mes_ultimo)
    else:
        hoy = date.today()
        anio_inicio, mes_inicio = hoy.year, hoy.month

    for entrada in entradas:
        if not entrada.pagado:
            session.delete(entrada)

    concepto.valor_total = valor_total
    concepto.tasa_interes = tasa_interes
    concepto.periodo_tasa = periodo_tasa
    concepto.numero_cuotas = numero_cuotas
    session.add(concepto)
    session.commit()
    session.refresh(concepto)

    return concepto, anio_inicio, mes_inicio, siguiente_numero


def activar_amortizacion(
    session: Session,
    user_id: int,
    concepto_id: int,
    *,
    valor_total: Decimal,
    tasa_interes: Decimal,
    periodo_tasa: PeriodoTasa,
    numero_cuotas: int,
    cuota_inicial: int | None,
) -> tuple[Concepto, int, int]:
    """Sets amortization terms for the first time on a debt concept that
    doesn't yet have them. Unlike actualizar_amortizacion, this behaves like
    fresh creation math-wise: anchored at today, cuota_inicial comes purely
    from the caller (not derived from paid-entry count) - see design.md.
    Every not-yet-paid entry is deleted; paid ones are left untouched as
    historical record. Returns (concepto, anio_inicio, mes_inicio) for the
    router to pass into entry_service.generar_entradas_amortizacion."""
    concepto = get_concepto(session, user_id, concepto_id)
    if concepto.tipo != TipoConcepto.DEUDA:
        raise ValueError("amortization terms only apply to concepts of type 'deuda'")
    if es_amortizada(concepto):
        raise ValueError(
            "this concept already has amortization terms; use the correction "
            "endpoint instead"
        )

    entradas = list(
        session.exec(select(EntradaMensual).where(EntradaMensual.concepto_id == concepto.id))
    )
    for entrada in entradas:
        if not entrada.pagado:
            session.delete(entrada)

    concepto.valor_total = valor_total
    concepto.tasa_interes = tasa_interes
    concepto.periodo_tasa = periodo_tasa
    concepto.numero_cuotas = numero_cuotas
    concepto.cuota_inicial = cuota_inicial
    session.add(concepto)
    session.commit()
    session.refresh(concepto)

    hoy = date.today()
    return concepto, hoy.year, hoy.month


def delete_concepto(session: Session, user_id: int, concepto_id: int) -> None:
    concepto = get_concepto(session, user_id, concepto_id)
    session.delete(concepto)
    session.commit()


def valor_total_efectivo(concepto: Concepto) -> Decimal | None:
    """The debt's starting amount for saldo_restante purposes - valor_total,
    unless cuota_inicial skips past some installments, in which case it's the
    schedule's balance right after the installment before cuota_inicial (those
    earlier installments never have entries or monto_pagado in this system)."""
    if concepto.valor_total is None:
        return None
    if not concepto.cuota_inicial or concepto.cuota_inicial <= 1 or not es_amortizada(concepto):
        return concepto.valor_total
    tasa_mensual = tasa_mensual_desde(concepto.tasa_interes, concepto.periodo_tasa)
    tabla = generar_tabla_amortizacion(concepto.valor_total, tasa_mensual, concepto.numero_cuotas)
    return tabla[concepto.cuota_inicial - 2]["saldo"]


def saldo_restante(session: Session, concepto: Concepto) -> Decimal | None:
    if concepto.tipo != TipoConcepto.DEUDA or concepto.valor_total is None:
        return None
    total_pagado = session.exec(
        select(func.coalesce(func.sum(EntradaMensual.monto_pagado), 0)).where(
            EntradaMensual.concepto_id == concepto.id
        )
    ).one()
    # Principal prepayments recorded via registrar_abono_capital also reduce
    # the balance. Unlike Deudor's Abono, AbonoCapitalConcepto has no
    # pre-existing rows and no historical-abono ambiguity to guard against
    # (see design.md, add-abono-sobrante), so every row here always counts.
    total_abonos_capital = session.exec(
        select(func.coalesce(func.sum(AbonoCapitalConcepto.monto), 0)).where(
            AbonoCapitalConcepto.concepto_id == concepto.id
        )
    ).one()
    restante = (
        valor_total_efectivo(concepto) - Decimal(total_pagado) - Decimal(total_abonos_capital)
    )
    return restante if restante > 0 else Decimal("0")


def cuota_fija(session: Session, concepto: Concepto) -> Decimal | None:
    """Reads the fixed installment from the actual schedule (the next
    not-yet-paid entry's planned amount) rather than recomputing it from
    stored terms - see design.md (add-abono-sobrante): a principal
    prepayment can change the remaining schedule without touching
    valor_total/numero_cuotas, which stay as historical record of the
    original debt. Falls back to the most recent entry if none are unpaid,
    or the stored-terms computation if no schedule exists at all yet."""
    if not es_amortizada(concepto) or concepto.valor_total is None:
        return None
    proxima = session.exec(
        select(EntradaMensual)
        .where(EntradaMensual.concepto_id == concepto.id, EntradaMensual.pagado.is_(False))
        .order_by(EntradaMensual.anio, EntradaMensual.mes)
    ).first()
    if proxima is not None:
        return proxima.monto_planeado
    ultima = session.exec(
        select(EntradaMensual)
        .where(EntradaMensual.concepto_id == concepto.id)
        .order_by(EntradaMensual.anio.desc(), EntradaMensual.mes.desc())
    ).first()
    if ultima is not None:
        return ultima.monto_planeado
    tasa_mensual = tasa_mensual_desde(concepto.tasa_interes, concepto.periodo_tasa)
    return calcular_cuota_fija(concepto.valor_total, tasa_mensual, concepto.numero_cuotas)


def registrar_abono_capital(
    session: Session,
    user_id: int,
    concepto_id: int,
    *,
    monto: Decimal,
    fecha: date,
    modo: str,
) -> Concepto:
    """Records an extraordinary principal prepayment against an amortized
    debt concept - see design.md (add-abono-sobrante). Straight port of
    deudor_service.registrar_abono_capital: valor_total/numero_cuotas stay as
    historical record of the original debt (only numero_cuotas is bumped to
    reflect the new total installment count); the reduction is tracked via an
    AbonoCapitalConcepto row instead, which saldo_restante now also
    subtracts. Fully settling the balance closes the concept, mirroring the
    existing activo/finalizado_en transition."""
    concepto = get_concepto(session, user_id, concepto_id)
    if not es_amortizada(concepto):
        raise ValueError(
            "principal prepayments only apply to amortized debts; use a "
            "regular payment instead"
        )

    abono = AbonoCapitalConcepto(concepto_id=concepto.id, monto=monto, fecha=fecha)
    session.add(abono)
    session.commit()

    nuevo_saldo = saldo_restante(session, concepto)

    entradas = list(
        session.exec(select(EntradaMensual).where(EntradaMensual.concepto_id == concepto.id))
    )

    if nuevo_saldo <= 0:
        for entrada in entradas:
            if not entrada.pagado:
                session.delete(entrada)
        if concepto.activo:
            concepto.activo = False
            concepto.finalizado_en = date.today()
            session.add(concepto)
        session.commit()
        session.refresh(concepto)
        return concepto

    pagadas = [e for e in entradas if e.pagado]
    n_pagadas = len(pagadas)
    siguiente_numero = (concepto.cuota_inicial or 1) + n_pagadas

    if pagadas:
        anio_ultimo, mes_ultimo = max((e.anio, e.mes) for e in pagadas)
        anio_inicio, mes_inicio = _sumar_un_mes(anio_ultimo, mes_ultimo)
    else:
        hoy = date.today()
        anio_inicio, mes_inicio = hoy.year, hoy.month

    tasa_mensual = tasa_mensual_desde(concepto.tasa_interes, concepto.periodo_tasa)
    cuota_fija_actual = cuota_fija(session, concepto)

    if modo == "reducir_cuota":
        numero_cuotas_restantes = concepto.numero_cuotas - siguiente_numero + 1
    elif modo == "reducir_plazo":
        numero_cuotas_restantes = calcular_cuotas_restantes(nuevo_saldo, tasa_mensual, cuota_fija_actual)
    else:
        raise ValueError("modo must be 'reducir_plazo' or 'reducir_cuota'")

    if numero_cuotas_restantes <= 0:
        raise ValueError("this concept's schedule has no remaining installments to adjust")

    for entrada in entradas:
        if not entrada.pagado:
            session.delete(entrada)

    concepto.numero_cuotas = (siguiente_numero - 1) + numero_cuotas_restantes
    session.add(concepto)
    session.commit()
    session.refresh(concepto)

    tabla = generar_tabla_amortizacion(nuevo_saldo, tasa_mensual, numero_cuotas_restantes)
    entry_service.generar_entradas_amortizacion(
        session, concepto, tabla, anio_inicio, mes_inicio, cuota_inicial=1
    )
    return concepto


def registrar_pago_con_sobrante(
    session: Session,
    user_id: int,
    concepto_id: int,
    *,
    anio: int,
    mes: int,
    monto_planeado: Decimal,
    monto_pagado: Decimal,
    modo: str,
) -> EntradaMensual:
    """Marks a monthly entry paid, capping its stored monto_pagado to
    monto_planeado, and routes the surplus into a principal prepayment via
    registrar_abono_capital - all in one call, so the balance never
    double-counts the surplus (see design.md, add-abono-sobrante). Rejects
    if the concept isn't amortized or if monto_pagado doesn't exceed
    monto_planeado (nothing to route)."""
    concepto = get_concepto(session, user_id, concepto_id)
    if not es_amortizada(concepto):
        raise ValueError(
            "routing a payment surplus into a principal prepayment only "
            "applies to amortized debts"
        )
    if monto_pagado <= monto_planeado:
        raise ValueError("no hay sobrante que registrar como abono a capital")

    entry = entry_service.upsert_monthly_entry(
        session,
        concepto,
        anio,
        mes,
        monto_planeado=monto_planeado,
        monto_pagado=monto_planeado,
        pagado=True,
    )
    excedente = monto_pagado - monto_planeado
    registrar_abono_capital(
        session, user_id, concepto_id, monto=excedente, fecha=entry.fecha_pago, modo=modo
    )
    session.refresh(entry)
    return entry
