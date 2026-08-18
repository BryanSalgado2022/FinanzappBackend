from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

# Fixed, backend-owned set of emojis a Categoria may use - the frontend uses
# the identical list for its picker. Chosen to cover the shapes already
# present in the user's real category names (Vivienda->house, Celular->phone,
# Creditos/Prestamos->card, Sueldo/Salario/Primas->money).
ALLOWED_CATEGORIA_EMOJIS = (
    "💰",
    "🏦",
    "💳",
    "🏠",
    "🚗",
    "🍽️",
    "💊",
    "✈️",
    "🎂",
    "❤️",
    "🎯",
    "💡",
    "💧",
    "🛒",
    "📅",
    "📱",
)


class Categoria(SQLModel, table=True):
    __tablename__ = "categorias"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    nombre: str
    emoji: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConceptoCategoria(SQLModel, table=True):
    __tablename__ = "concepto_categoria"

    concepto_id: int = Field(foreign_key="concepts.id", primary_key=True, ondelete="CASCADE")
    categoria_id: int = Field(foreign_key="categorias.id", primary_key=True, ondelete="CASCADE")
