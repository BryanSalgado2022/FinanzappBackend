from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.models.deudor import CuotaDeudor, Deudor


class CuotaNotFoundError(Exception):
    pass


def get_cuota(session: Session, deudor_id: int, anio: int, mes: int) -> CuotaDeudor | None:
    return session.exec(
        select(CuotaDeudor).where(
            CuotaDeudor.deudor_id == deudor_id,
            CuotaDeudor.anio == anio,
            CuotaDeudor.mes == mes,
        )
    ).first()


def list_cuotas(session: Session, deudor_id: int) -> list[CuotaDeudor]:
    return list(
        session.exec(
            select(CuotaDeudor)
            .where(CuotaDeudor.deudor_id == deudor_id)
            .order_by(CuotaDeudor.anio, CuotaDeudor.mes)
        )
    )


def _sumar_meses(anio: int, mes: int, cantidad: int) -> tuple[int, int]:
    total = (anio * 12 + (mes - 1)) + cantidad
    return total // 12, total % 12 + 1


def generar_cuotas_amortizacion(
    session: Session,
    deudor: Deudor,
    tabla: list[dict],
    anio_inicio: int,
    mes_inicio: int,
    cuota_inicial: int = 1,
) -> None:
    """Creates one CuotaDeudor per installment in an amortization schedule
    from cuota_inicial through the end of tabla, starting at anio_inicio/
    mes_inicio (the first *generated* installment always lands there,
    regardless of its number in the schedule) and spanning as many years as
    needed. Never overwrites an existing row for the same (deudor_id, anio,
    mes) - mirrors entry_service.generar_entradas_amortizacion."""
    for fila in tabla:
        if fila["numero"] < cuota_inicial:
            continue
        anio, mes = _sumar_meses(anio_inicio, mes_inicio, fila["numero"] - cuota_inicial)
        if get_cuota(session, deudor.id, anio, mes) is not None:
            continue
        session.add(
            CuotaDeudor(
                deudor_id=deudor.id,
                anio=anio,
                mes=mes,
                monto_planeado=fila["cuota"],
                interes=fila["interes"],
            )
        )
    session.commit()


def marcar_pagada(
    session: Session,
    deudor: Deudor,
    anio: int,
    mes: int,
    *,
    monto_pagado: Decimal | None,
    pagado: bool,
) -> CuotaDeudor:
    cuota = get_cuota(session, deudor.id, anio, mes)
    if cuota is None:
        raise CuotaNotFoundError()
    cuota.monto_pagado = monto_pagado if monto_pagado is not None else (cuota.monto_planeado if pagado else None)
    # Only on an actual pagado transition, not every save of an already-paid
    # cuota - otherwise fecha_pago would get bumped to today on every
    # unrelated edit. Mirrors entry_service._save_entry.
    if pagado and not cuota.pagado:
        cuota.fecha_pago = date.today()
    elif not pagado:
        cuota.fecha_pago = None
    cuota.pagado = pagado
    session.add(cuota)
    session.commit()
    session.refresh(cuota)
    return cuota
