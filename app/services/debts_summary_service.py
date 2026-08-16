from decimal import Decimal

from sqlmodel import Session, select

from app.models.concepto import Concepto, TipoConcepto
from app.schemas.debts_summary import AnnualMonthTotal, AnnualTrend, DebtComposition, DebtsSummary
from app.services import concept_service
from app.services.summary_service import monthly_summary


def debts_summary(session: Session, user_id: int) -> DebtsSummary:
    deudas = session.exec(
        select(Concepto).where(Concepto.user_id == user_id, Concepto.tipo == TipoConcepto.DEUDA)
    ).all()

    total_adeudado = Decimal("0")
    total_restante = Decimal("0")
    composicion: list[DebtComposition] = []
    for deuda in deudas:
        restante = concept_service.saldo_restante(session, deuda) or Decimal("0")
        if deuda.valor_total is not None:
            total_adeudado += deuda.valor_total
        total_restante += restante
        composicion.append(
            DebtComposition(concepto_id=deuda.id, nombre=deuda.nombre, saldo_restante=restante)
        )

    total_pagado = total_adeudado - total_restante
    progreso = (total_pagado / total_adeudado * 100) if total_adeudado > 0 else Decimal("0")

    return DebtsSummary(
        numero_deudas=len(deudas),
        total_adeudado=total_adeudado,
        total_pagado=total_pagado,
        saldo_total_restante=total_restante,
        progreso_porcentaje=progreso.quantize(Decimal("0.01")),
        composicion=composicion,
    )


def annual_trend(session: Session, user_id: int, anio: int) -> AnnualTrend:
    meses = []
    for mes in range(1, 13):
        resumen = monthly_summary(session, user_id, anio, mes)
        meses.append(
            AnnualMonthTotal(
                mes=mes, total_ingresos=resumen.total_ingresos, total_gastos=resumen.total_gastos
            )
        )
    return AnnualTrend(anio=anio, meses=meses)
