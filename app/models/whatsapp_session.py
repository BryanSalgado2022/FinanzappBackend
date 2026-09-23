from datetime import datetime

from sqlmodel import Field, SQLModel


class WhatsAppSession(SQLModel, table=True):
    """One row per linked phone number, holding that number's single pending
    WhatsApp turn - see whatsapp_service.py and design.md (add-whatsapp-agent).
    Never appended to, always upserted: a phone number has at most one
    pending turn at a time, which is either a proposed action awaiting a
    yes/no reply, or a clarifying question awaiting its answer."""

    __tablename__ = "whatsapp_sessions"

    phone_number: str = Field(primary_key=True)
    # Serialized ProposedActionResponse or ClarificationNeededResponse
    # (app/schemas/agent.py) - reused as-is, tagged by its own `type` field.
    pending_response_json: str | None = Field(default=None)
    # Only set for a pending clarification - the original user message,
    # needed to reconstruct a small context when the answer arrives.
    pending_original_message: str | None = Field(default=None)
    expires_at: datetime | None = Field(default=None)
