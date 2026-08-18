from pydantic import BaseModel, model_validator

from app.models.categoria import ALLOWED_CATEGORIA_EMOJIS


def _validate_emoji(emoji: str | None) -> None:
    if emoji is not None and emoji not in ALLOWED_CATEGORIA_EMOJIS:
        raise ValueError(f"emoji must be one of {ALLOWED_CATEGORIA_EMOJIS}")


class CategoriaCreate(BaseModel):
    nombre: str
    emoji: str | None = None

    @model_validator(mode="after")
    def validate_emoji(self) -> "CategoriaCreate":
        _validate_emoji(self.emoji)
        return self


class CategoriaUpdate(BaseModel):
    nombre: str | None = None
    emoji: str | None = None

    @model_validator(mode="after")
    def validate_emoji(self) -> "CategoriaUpdate":
        _validate_emoji(self.emoji)
        return self


class CategoriaRead(BaseModel):
    id: int
    nombre: str
    emoji: str | None
