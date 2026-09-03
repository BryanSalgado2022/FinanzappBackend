from pydantic import BaseModel


class IcsTokenRead(BaseModel):
    ics_token: str
