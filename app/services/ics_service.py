from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models.concepto import Concepto, TipoConcepto
from app.models.deudor import Abono, Deudor
from app.models.entrada_mensual import EntradaMensual
from app.models.gasto import Gasto
from app.models.tarea import Tarea
from app.models.user import User
from app.services.concept_service import saldo_restante

WINDOW_BACK_DAYS = 92  # ~3 months
WINDOW_FORWARD_DAYS = 366  # ~12 months


@dataclass
class _Event:
    fecha: date
    uid: str
    summary: str
    description: str


def _in_window(fecha: date | None, desde: date, hasta: date) -> bool:
    return fecha is not None and desde <= fecha <= hasta


def _celebracion_pago(session: Session, concepto: Concepto) -> date | None:
    """Mirrors agendaEvents.ts's findCelebracionPago: the most recently paid
    entry's date, but only when it zeroed out the debt's balance."""
    if concepto.tipo != TipoConcepto.DEUDA:
        return None
    saldo = saldo_restante(session, concepto)
    if saldo is None or saldo != 0:
        return None
    entries = session.exec(
        select(EntradaMensual).where(
            EntradaMensual.concepto_id == concepto.id, EntradaMensual.pagado.is_(True)
        )
    ).all()
    fechas = [e.fecha_pago for e in entries if e.fecha_pago is not None]
    return max(fechas) if fechas else None


def _collect_events(session: Session, user: User, desde: date, hasta: date) -> list[_Event]:
    events: list[_Event] = []

    conceptos = session.exec(select(Concepto).where(Concepto.user_id == user.id)).all()
    for concepto in conceptos:
        if concepto.dia_vencimiento is not None:
            entries = session.exec(
                select(EntradaMensual).where(EntradaMensual.concepto_id == concepto.id)
            ).all()
            for entry in entries:
                try:
                    fecha = date(entry.anio, entry.mes, concepto.dia_vencimiento)
                except ValueError:
                    continue
                if _in_window(fecha, desde, hasta):
                    monto = entry.monto_pagado if entry.pagado else entry.monto_planeado
                    estado = "pagado" if entry.pagado else "pendiente"
                    events.append(
                        _Event(
                            fecha=fecha,
                            uid=f"concepto-{concepto.id}-{entry.anio}-{entry.mes}",
                            summary=f"{concepto.nombre} ({estado})",
                            description=f"{concepto.tipo.value} - {monto}",
                        )
                    )

        if _in_window(concepto.finalizado_en, desde, hasta):
            events.append(
                _Event(
                    fecha=concepto.finalizado_en,
                    uid=f"concepto-cierre-{concepto.id}",
                    summary=f"{concepto.nombre} - finalizado",
                    description="Concepto finalizado",
                )
            )

        celebracion = _celebracion_pago(session, concepto)
        if _in_window(celebracion, desde, hasta):
            events.append(
                _Event(
                    fecha=celebracion,
                    uid=f"concepto-celebracion-{concepto.id}",
                    summary=f"🎉 {concepto.nombre} - deuda saldada",
                    description="Esta deuda quedó completamente pagada",
                )
            )

    gastos = session.exec(select(Gasto).where(Gasto.user_id == user.id)).all()
    for gasto in gastos:
        if _in_window(gasto.fecha, desde, hasta):
            events.append(
                _Event(
                    fecha=gasto.fecha,
                    uid=f"gasto-{gasto.id}",
                    summary=gasto.descripcion,
                    description=f"Gasto: {gasto.monto}",
                )
            )

    tareas = session.exec(select(Tarea).where(Tarea.user_id == user.id)).all()
    for tarea in tareas:
        if _in_window(tarea.fecha, desde, hasta):
            events.append(
                _Event(
                    fecha=tarea.fecha,
                    uid=f"tarea-{tarea.id}",
                    summary=tarea.titulo,
                    description=tarea.nota or "Tarea",
                )
            )

    deudores = session.exec(select(Deudor).where(Deudor.user_id == user.id)).all()
    for deudor in deudores:
        if _in_window(deudor.fecha, desde, hasta):
            events.append(
                _Event(
                    fecha=deudor.fecha,
                    uid=f"deudor-inicio-{deudor.id}",
                    summary=f"Préstamo a {deudor.nombre}",
                    description=f"Monto prestado: {deudor.monto_total}",
                )
            )
        if _in_window(deudor.finalizado_en, desde, hasta):
            events.append(
                _Event(
                    fecha=deudor.finalizado_en,
                    uid=f"deudor-cierre-{deudor.id}",
                    summary=f"{deudor.nombre} - deuda saldada",
                    description="Este deudor terminó de pagar",
                )
            )

        abonos = session.exec(select(Abono).where(Abono.deudor_id == deudor.id)).all()
        for abono in abonos:
            if _in_window(abono.fecha, desde, hasta):
                events.append(
                    _Event(
                        fecha=abono.fecha,
                        uid=f"abono-{abono.id}",
                        summary=f"Abono de {deudor.nombre}",
                        description=f"Monto: {abono.monto}",
                    )
                )

    return events


def _escape_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def _format_event(event: _Event, dtstamp: str) -> list[str]:
    dtstart = event.fecha.strftime("%Y%m%d")
    return [
        "BEGIN:VEVENT",
        f"UID:{event.uid}@tobe",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;VALUE=DATE:{dtstart}",
        f"SUMMARY:{_escape_text(event.summary)}",
        f"DESCRIPTION:{_escape_text(event.description)}",
        "END:VEVENT",
    ]


def generate_ics(session: Session, user: User) -> str:
    today = date.today()
    desde = today - timedelta(days=WINDOW_BACK_DAYS)
    hasta = today + timedelta(days=WINDOW_FORWARD_DAYS)
    events = _collect_events(session, user, desde, hasta)
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TOBE//Calendar Export//ES",
        "CALSCALE:GREGORIAN",
    ]
    for event in events:
        lines.extend(_format_event(event, dtstamp))
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
