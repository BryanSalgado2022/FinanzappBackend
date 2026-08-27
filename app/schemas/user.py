from datetime import date
from decimal import Decimal

from pydantic import BaseModel, model_validator

from app.models.user import ALLOWED_ACCENT_COLORS


class UserRead(BaseModel):
    id: int
    email: str
    name: str
    color_acento: str | None
    ahorros: Decimal | None
    saldo_disponible_inicial: Decimal | None
    saldo_disponible_fecha: date | None


class UserUpdate(BaseModel):
    color_acento: str | None = None
    ahorros: Decimal | None = None
    saldo_disponible_inicial: Decimal | None = None

    @model_validator(mode="after")
    def validate_color_acento(self) -> "UserUpdate":
        if self.color_acento is not None and self.color_acento not in ALLOWED_ACCENT_COLORS:
            raise ValueError(f"color_acento must be one of {ALLOWED_ACCENT_COLORS}")
        return self
