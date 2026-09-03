from pydantic import BaseModel


class IcsTokenRead(BaseModel):
    ics_token: str


class IcsTokenStatus(BaseModel):
    ics_token: str | None
