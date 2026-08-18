from datetime import date, time

from sqlmodel import Session, select

from app.models.tarea import Tarea


class TareaNotFoundError(Exception):
    pass


def es_vencida(fecha: date | None, completada: bool) -> bool:
    if fecha is None or completada:
        return False
    return fecha < date.today()


def create_tarea(
    session: Session,
    user_id: int,
    titulo: str,
    *,
    emoji: str | None = None,
    fecha: date | None = None,
    hora: time | None = None,
    nota: str | None = None,
) -> Tarea:
    tarea = Tarea(
        user_id=user_id,
        titulo=titulo,
        emoji=emoji,
        fecha=fecha,
        hora=hora,
        nota=nota,
    )
    session.add(tarea)
    session.commit()
    session.refresh(tarea)
    return tarea


def get_tarea(session: Session, user_id: int, tarea_id: int) -> Tarea:
    tarea = session.get(Tarea, tarea_id)
    if tarea is None or tarea.user_id != user_id:
        raise TareaNotFoundError(tarea_id)
    return tarea


def list_tareas(session: Session, user_id: int) -> list[Tarea]:
    return list(session.exec(select(Tarea).where(Tarea.user_id == user_id)))


def update_tarea(
    session: Session,
    user_id: int,
    tarea_id: int,
    *,
    titulo: str | None = None,
    emoji: str | None = None,
    fecha: date | None = None,
    hora: time | None = None,
    nota: str | None = None,
    completada: bool | None = None,
) -> Tarea:
    tarea = get_tarea(session, user_id, tarea_id)
    if titulo is not None:
        tarea.titulo = titulo
    if emoji is not None:
        tarea.emoji = emoji
    if fecha is not None:
        tarea.fecha = fecha
    if hora is not None:
        tarea.hora = hora
    if nota is not None:
        tarea.nota = nota
    if completada is not None:
        tarea.completada = completada
    session.add(tarea)
    session.commit()
    session.refresh(tarea)
    return tarea


def delete_tarea(session: Session, user_id: int, tarea_id: int) -> None:
    tarea = get_tarea(session, user_id, tarea_id)
    session.delete(tarea)
    session.commit()
