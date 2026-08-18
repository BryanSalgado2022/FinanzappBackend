from datetime import date, time

from pydantic import BaseModel, model_validator

from app.models.tarea import ALLOWED_TAREA_EMOJIS


def _validate_emoji(emoji: str | None) -> None:
    if emoji is not None and emoji not in ALLOWED_TAREA_EMOJIS:
        raise ValueError(f"emoji must be one of {ALLOWED_TAREA_EMOJIS}")


class TareaCreate(BaseModel):
    titulo: str
    emoji: str | None = None
    fecha: date | None = None
    hora: time | None = None
    nota: str | None = None

    @model_validator(mode="after")
    def validate_emoji(self) -> "TareaCreate":
        _validate_emoji(self.emoji)
        return self


class TareaUpdate(BaseModel):
    titulo: str | None = None
    emoji: str | None = None
    fecha: date | None = None
    hora: time | None = None
    nota: str | None = None
    completada: bool | None = None

    @model_validator(mode="after")
    def validate_emoji(self) -> "TareaUpdate":
        _validate_emoji(self.emoji)
        return self


class TareaRead(BaseModel):
    id: int
    titulo: str
    emoji: str | None
    fecha: date | None
    hora: time | None
    nota: str | None
    completada: bool
    vencida: bool
