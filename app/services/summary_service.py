from decimal import Decimal

from sqlalchemy import case, extract
from sqlmodel import Session, func, select

from app.models.concepto import Concepto, TipoConcepto
from app.models.deudor import Abono, Deudor
from app.models.entrada_mensual import EntradaMensual
from app.models.gasto import Gasto
from app.models.user import User
from app.schemas.summary import MonthlySummary
from app.services.gasto_service import sum_gastos


def _sum_pagado_o_planeado(
    session: Session, user_id: int, anio: int, mes: int, tipos: tuple[TipoConcepto, ...]
) -> Decimal:
    # A paid entry's real monto_pagado can differ from what was planned
    # (partial or over payment) - the summary must reflect what actually
    # moved, not the plan, once it's known. Unpaid entries have no
    # monto_pagado yet, so monto_planeado remains the only figure available
    # for those. See openspec fix-monthly-summary-uses-real-amounts.
    monto_real = case(
        (EntradaMensual.pagado, EntradaMensual.monto_pagado),
        else_=EntradaMensual.monto_planeado,
    )
    result = session.exec(
        select(func.coalesce(func.sum(monto_real), 0))
        .join(Concepto, Concepto.id == EntradaMensual.concepto_id)
        .where(
            Concepto.user_id == user_id,
            Concepto.tipo.in_(tipos),
            EntradaMensual.anio == anio,
            EntradaMensual.mes == mes,
        )
    ).one()
    return Decimal(result)


def _sum_abono_interes(session: Session, user_id: int, anio: int, mes: int) -> Decimal:
    result = session.exec(
        select(func.coalesce(func.sum(Abono.interes), 0))
        .join(Deudor, Deudor.id == Abono.deudor_id)
        .where(
            Deudor.user_id == user_id,
            extract("year", Abono.fecha) == anio,
            extract("month", Abono.fecha) == mes,
        )
    ).one()
    return Decimal(result)


def monthly_summary(session: Session, user_id: int, anio: int, mes: int) -> MonthlySummary:
    total_ingresos = _sum_pagado_o_planeado(
        session, user_id, anio, mes, (TipoConcepto.INGRESO,)
    ) + _sum_abono_interes(session, user_id, anio, mes)
    total_gastos = _sum_pagado_o_planeado(
        session, user_id, anio, mes, (TipoConcepto.DEUDA, TipoConcepto.GASTO_FIJO)
    ) + sum_gastos(session, user_id, anio, mes)
    return MonthlySummary(
        anio=anio,
        mes=mes,
        total_ingresos=total_ingresos,
        total_gastos=total_gastos,
        balance_neto=total_ingresos - total_gastos,
    )


def _sum_pagado(
    session: Session, user_id: int, fecha_desde, tipos: tuple[TipoConcepto, ...]
) -> Decimal:
    # monto_pagado, never monto_planeado - a partial payment (planned
    # 100.000, actually paid 50.000) must only count for the 50.000 that
    # actually moved. entry_service._save_entry guarantees monto_pagado is
    # never null once pagado is true, so no coalesce is needed here.
    result = session.exec(
        select(func.coalesce(func.sum(EntradaMensual.monto_pagado), 0))
        .join(Concepto, Concepto.id == EntradaMensual.concepto_id)
        .where(
            Concepto.user_id == user_id,
            Concepto.tipo.in_(tipos),
            EntradaMensual.pagado.is_(True),
            EntradaMensual.fecha_pago >= fecha_desde,
        )
    ).one()
    return Decimal(result)


def _sum_gastos_desde(session: Session, user_id: int, fecha_desde) -> Decimal:
    result = session.exec(
        select(func.coalesce(func.sum(Gasto.monto), 0)).where(
            Gasto.user_id == user_id, Gasto.fecha >= fecha_desde
        )
    ).one()
    return Decimal(result)


def _sum_abono_interes_desde(session: Session, user_id: int, fecha_desde) -> Decimal:
    result = session.exec(
        select(func.coalesce(func.sum(Abono.interes), 0))
        .join(Deudor, Deudor.id == Abono.deudor_id)
        .where(Deudor.user_id == user_id, Abono.fecha >= fecha_desde)
    ).one()
    return Decimal(result)


def disponible(session: Session, user: User) -> Decimal | None:
    if user.saldo_disponible_fecha is None:
        return None
    fecha_desde = user.saldo_disponible_fecha
    ingresos_pagados = _sum_pagado(session, user.id, fecha_desde, (TipoConcepto.INGRESO,))
    gastos_pagados = _sum_pagado(
        session, user.id, fecha_desde, (TipoConcepto.DEUDA, TipoConcepto.GASTO_FIJO)
    )
    intereses = _sum_abono_interes_desde(session, user.id, fecha_desde)
    gastos_variables = _sum_gastos_desde(session, user.id, fecha_desde)
    inicial = user.saldo_disponible_inicial or Decimal(0)
    return inicial + ingresos_pagados + intereses - gastos_pagados - gastos_variables
