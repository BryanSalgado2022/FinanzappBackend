from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel

# Fixed, backend-owned set of accent color identifiers a user may choose -
# the frontend maps each identifier to its own light/dark hex pair. The
# backend has no color/CSS knowledge, it only validates and stores the id.
ALLOWED_ACCENT_COLORS = (
    "verde",
    "azul",
    "morado",
    "rosa",
    "naranja",
    "amarillo",
    "rojo",
    "turquesa",
    "gris",
)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    google_sub: str | None = Field(default=None, unique=True, index=True)
    password_hash: str | None = Field(default=None)
    email: str = Field(unique=True, index=True)
    name: str
    # None means "use the app's default accent color" - a first-class valid
    # state, not merely "not yet set".
    color_acento: str | None = Field(default=None)
    # Manually-managed savings figure - never computed/adjusted by the app,
    # see openspec add-available-balance.
    ahorros: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    # Disponible baseline: "as of saldo_disponible_fecha, I had
    # saldo_disponible_inicial available." Re-set together (never
    # independently) whenever the user edits their starting figure - see
    # app/routers/users.py.
    saldo_disponible_inicial: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    saldo_disponible_fecha: date | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
