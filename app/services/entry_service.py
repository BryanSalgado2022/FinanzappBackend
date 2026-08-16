from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.models.concepto import Concepto, TipoConcepto
from app.models.entrada_mensual import EntradaMensual

RECURRING_TYPES = (TipoConcepto.DEUDA, TipoConcepto.GASTO_FIJO, TipoConcepto.INGRESO)


def get_entry(session: Session, concepto_id: int, anio: int, mes: int) -> EntradaMensual | None:
    return session.exec(
        select(EntradaMensual).where(
            EntradaMensual.concepto_id == concepto_id,
            EntradaMensual.anio == anio,
            EntradaMensual.mes == mes,
        )
    ).first()


def list_entries(session: Session, concepto_id: int) -> list[EntradaMensual]:
    return list(
        session.exec(
            select(EntradaMensual)
            .where(EntradaMensual.concepto_id == concepto_id)
            .order_by(EntradaMensual.anio, EntradaMensual.mes)
        )
    )


def _save_entry(
    session: Session,
    concepto_id: int,
    anio: int,
    mes: int,
    *,
    monto_planeado: Decimal,
    monto_pagado: Decimal | None,
    pagado: bool,
) -> EntradaMensual:
    entry = get_entry(session, concepto_id, anio, mes)
    if entry is None:
        entry = EntradaMensual(concepto_id=concepto_id, anio=anio, mes=mes)
    entry.monto_planeado = monto_planeado
    # Marking an entry paid without a specific amount means "I paid what was
    # planned" - saldo_restante and the debts summary sum monto_pagado, not
    # the pagado flag, so leaving it null here would silently not count it.
    entry.monto_pagado = monto_pagado if monto_pagado is not None else (monto_planeado if pagado else None)
    entry.pagado = pagado
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def _fill_forward(
    session: Session, concepto: Concepto, monto_planeado: Decimal, anio: int, desde_mes: int
) -> None:
    """Create entries for `desde_mes`..12 of `anio` using `monto_planeado`,
    skipping any month that already has an entry (never overwrite)."""
    for mes in range(desde_mes, 13):
        if get_entry(session, concepto.id, anio, mes) is not None:
            continue
        session.add(
            EntradaMensual(concepto_id=concepto.id, anio=anio, mes=mes, monto_planeado=monto_planeado)
        )
    session.commit()


def _sumar_meses(anio: int, mes: int, cantidad: int) -> tuple[int, int]:
    total = (anio * 12 + (mes - 1)) + cantidad
    return total // 12, total % 12 + 1


def generar_entradas_amortizacion(
    session: Session,
    concepto: Concepto,
    tabla: list[dict],
    anio_inicio: int,
    mes_inicio: int,
) -> None:
    """Creates one monthly entry per installment in an amortization schedule,
    starting at anio_inicio/mes_inicio and spanning as many years as needed.
    Never overwrites an existing entry, matching _fill_forward's guarantee."""
    for fila in tabla:
        anio, mes = _sumar_meses(anio_inicio, mes_inicio, fila["numero"] - 1)
        if get_entry(session, concepto.id, anio, mes) is not None:
            continue
        session.add(
            EntradaMensual(concepto_id=concepto.id, anio=anio, mes=mes, monto_planeado=fila["cuota"])
        )
    session.commit()


def generar_entradas_recurrentes(
    session: Session,
    concepto: Concepto,
    monto_planeado: Decimal,
    anio_inicio: int,
    mes_inicio: int,
    duracion_meses: int,
) -> None:
    """Creates exactly `duracion_meses` consecutive monthly entries starting at
    anio_inicio/mes_inicio, all using the same flat monto_planeado, spanning as
    many years as needed. Mirrors generar_entradas_amortizacion's shape (known
    length, generated fully at creation) but with a flat amount instead of a
    computed schedule. Never overwrites an existing entry."""
    for offset in range(duracion_meses):
        anio, mes = _sumar_meses(anio_inicio, mes_inicio, offset)
        if get_entry(session, concepto.id, anio, mes) is not None:
            continue
        session.add(
            EntradaMensual(concepto_id=concepto.id, anio=anio, mes=mes, monto_planeado=monto_planeado)
        )
    session.commit()


def upsert_monthly_entry(
    session: Session,
    concepto: Concepto,
    anio: int,
    mes: int,
    *,
    monto_planeado: Decimal,
    monto_pagado: Decimal | None = None,
    pagado: bool = False,
) -> EntradaMensual:
    entry = _save_entry(
        session,
        concepto.id,
        anio,
        mes,
        monto_planeado=monto_planeado,
        monto_pagado=monto_pagado,
        pagado=pagado,
    )

    today = date.today()
    is_current_month = anio == today.year and mes == today.month
    tiene_ventana_fija = concepto.duracion_meses is not None or (
        concepto.tasa_interes is not None and concepto.numero_cuotas is not None
    )
    if (
        concepto.tipo in RECURRING_TYPES
        and concepto.activo
        and is_current_month
        and not tiene_ventana_fija
    ):
        _fill_forward(session, concepto, monto_planeado, anio, mes + 1)

    return entry
