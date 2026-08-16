from decimal import Decimal

from sqlmodel import Session, func, select

from app.models.concepto import Concepto, PeriodoTasa, TipoConcepto
from app.models.entrada_mensual import EntradaMensual
from app.services.amortization_service import calcular_cuota_fija, tasa_mensual_desde


class ConceptoNotFoundError(Exception):
    pass


def create_concepto(
    session: Session,
    user_id: int,
    nombre: str,
    tipo: TipoConcepto,
    categoria: str | None,
    valor_total: Decimal | None,
    *,
    tasa_interes: Decimal | None = None,
    periodo_tasa: PeriodoTasa | None = None,
    numero_cuotas: int | None = None,
    duracion_meses: int | None = None,
    dia_vencimiento: int | None = None,
) -> Concepto:
    concepto = Concepto(
        user_id=user_id,
        nombre=nombre,
        tipo=tipo,
        categoria=categoria,
        valor_total=valor_total,
        tasa_interes=tasa_interes,
        periodo_tasa=periodo_tasa,
        numero_cuotas=numero_cuotas,
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
    categoria: str | None = None,
    activo: bool | None = None,
    valor_total: Decimal | None = None,
    dia_vencimiento: int | None = None,
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
        if es_amortizada(concepto):
            raise ValueError(
                "valor_total cannot be changed on a debt with amortization data; "
                "delete this concept and create a new one instead"
            )
        concepto.valor_total = valor_total
    if dia_vencimiento is not None:
        if concepto.tipo == TipoConcepto.INGRESO:
            raise ValueError("dia_vencimiento is not allowed for concepts of type 'ingreso'")
        # No es_amortizada guard here, unlike valor_total above - dia_vencimiento
        # is informational only and never feeds a recalculation, so it stays
        # editable even on a locked amortized debt.
        concepto.dia_vencimiento = dia_vencimiento
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


def cuota_fija(concepto: Concepto) -> Decimal | None:
    if not es_amortizada(concepto) or concepto.valor_total is None:
        return None
    tasa_mensual = tasa_mensual_desde(concepto.tasa_interes, concepto.periodo_tasa)
    return calcular_cuota_fija(concepto.valor_total, tasa_mensual, concepto.numero_cuotas)
