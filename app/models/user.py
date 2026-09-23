from datetime import datetime, timezone

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
    # Secret, regenerable token identifying this user for the unauthenticated
    # calendar-subscribe endpoint - see app/routers/calendar.py. None until
    # the user first generates one.
    ics_token: str | None = Field(default=None, unique=True, index=True)
    # The WhatsApp number linked to this account (E.164, e.g. "+573001234567"),
    # set once the user completes the wa.me linking flow - see
    # app/services/whatsapp_service.py. None until linked.
    whatsapp_phone: str | None = Field(default=None, unique=True, index=True)
    # One-time secret sent as the prefilled wa.me message body to link a
    # phone number to this account - mirrors ics_token's shape. Regenerated
    # on each link attempt, cleared once consumed.
    whatsapp_link_token: str | None = Field(default=None, unique=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
