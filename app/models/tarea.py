from datetime import date, datetime, time, timezone

from sqlmodel import Field, SQLModel

# Fixed, backend-owned reminder-oriented emoji set for Tarea - separate from
# ALLOWED_CATEGORIA_EMOJIS (finance-oriented) since the two contexts call for
# different icons (clock/bell/phone/document here vs. money/bank there).
ALLOWED_TAREA_EMOJIS = (
    "✅",
    "⏰",
    "🔔",
    "📞",
    "📄",
    "☀️",
    "🎂",
    "🚗",
    "🍽️",
    "🏠",
    "💊",
    "❤️",
    "🎯",
    "✈️",
    "🛒",
    "⚡",
    "💧",
    "🏦",
    "💰",
    "📅",
)


class Tarea(SQLModel, table=True):
    __tablename__ = "tareas"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    titulo: str
    emoji: str | None = Field(default=None)
    fecha: date | None = Field(default=None)
    hora: time | None = Field(default=None)
    nota: str | None = Field(default=None)
    completada: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
