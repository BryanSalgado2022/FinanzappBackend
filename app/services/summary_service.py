from decimal import Decimal

from sqlalchemy import case, extract
from sqlmodel import Session, func, select

from app.models.concepto import Concepto, TipoConcepto
from app.models.deudor import Abono, Deudor
from app.models.entrada_mensual import EntradaMensual
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
