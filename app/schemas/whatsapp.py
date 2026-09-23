from pydantic import BaseModel


class WhatsAppLinkRead(BaseModel):
    token: str
    wa_link: str


class WhatsAppLinkStatus(BaseModel):
    linked: bool
    phone_number: str | None
