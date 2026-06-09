from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    AWAITING_APPOINTMENT = "awaiting_appointment"
    AWAITING_CALLBACK_TIME = "awaiting_callback_time"
    ENDED = "ended"


class Outcome(str, Enum):
    BOOKED = "booked"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    CALLBACK = "callback"
    DO_NOT_CALL = "do_not_call"
    WRONG_NUMBER = "wrong_number"
    VOICEMAIL = "voicemail"


class Message(BaseModel):
    role: Literal["assistant", "customer"]
    content: str
    timestamp: datetime


class AgentDecision(BaseModel):
    intent: str = Field(description="Short snake_case label for the customer's intent.")
    reply: str = Field(description="The exact short response to show to the customer.")
    next_status: ConversationStatus
    proposed_outcome: Outcome | None
    appointment_slot: str | None
    callback_time: str | None
    should_end: bool


class ConversationRecord(BaseModel):
    session_id: str
    customer_name: str
    status: ConversationStatus = ConversationStatus.ACTIVE
    outcome: Outcome | None = None
    appointment_slot: str | None = None
    callback_time: str | None = None
    do_not_call: bool = False
    previous_response_id: str | None = None
    latest_intent: str | None = None
    transcript: list[Message] = Field(default_factory=list)
    started_at: datetime
    ended_at: datetime | None = None

