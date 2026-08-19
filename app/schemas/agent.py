from datetime import date
from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "model"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    # The client's own local date - the server doesn't know the user's
    # timezone, so "hoy"/"ayer" are resolved against this, not the server clock.
    current_date: date


class ProposedActionResponse(BaseModel):
    type: Literal["proposed_action"] = "proposed_action"
    entity: Literal["gasto", "concepto", "tarea", "deudor", "abono"]
    fields: dict


class ClarificationNeededResponse(BaseModel):
    type: Literal["clarification_needed"] = "clarification_needed"
    message: str


class ReplyResponse(BaseModel):
    type: Literal["reply"] = "reply"
    message: str


ChatResponse = ProposedActionResponse | ClarificationNeededResponse | ReplyResponse
