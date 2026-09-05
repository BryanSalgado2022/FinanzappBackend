from datetime import date
from decimal import Decimal

from sqlmodel import Session, func, select

from app.models.categoria import Categoria
from app.models.concepto import Concepto, PeriodoTasa, TipoConcepto
from app.models.entrada_mensual import EntradaMensual
from app.services.amortization_service import (
    calcular_cuota_fija,
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
    restante = valor_total_efectivo(concepto) - Decimal(total_pagado)
    return restante if restante > 0 else Decimal("0")


def cuota_fija(concepto: Concepto) -> Decimal | None:
    if not es_amortizada(concepto) or concepto.valor_total is None:
        return None
    tasa_mensual = tasa_mensual_desde(concepto.tasa_interes, concepto.periodo_tasa)
    return calcular_cuota_fija(concepto.valor_total, tasa_mensual, concepto.numero_cuotas)
