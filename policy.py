from __future__ import annotations

import re
from datetime import datetime, timezone

from models import AgentDecision, ConversationRecord, ConversationStatus, Outcome

STORE_NAME = "Maple Carpet & Flooring"
DISCOUNT_PERCENT = 40
SALE_PERIOD = "this weekend only"
APPOINTMENT_TYPE = "free in-home measure"

APPOINTMENT_SLOTS = [
    "Saturday at 10:00 AM",
    "Saturday at 2:00 PM",
    "Sunday at 11:00 AM",
]

DO_NOT_CALL_REPLY = (
    "Of course. I've marked this number do not call, and we won't contact you "
    "again. Goodbye."
)
WRONG_NUMBER_REPLY = "I'm sorry about that. I'll mark this as a wrong number. Goodbye."
VOICEMAIL_REPLY = (
    "Hi, this is Maya, an AI assistant calling on behalf of Maple Carpet & "
    "Flooring. We're offering exactly 40% off this weekend only, with a free "
    "in-home measure. Please contact the store if you're interested."
)
SAFE_FALLBACK_REPLY = (
    "The in-home measure is free, and the confirmed offer is exactly 40% off "
    "this weekend only. I can help with the available times or have the store "
    "follow up."
)


class PolicyViolation(ValueError):
    pass


def normalize_message(message: str) -> str:
    lowered = message.lower().replace("’", "'")
    lowered = re.sub(r"[^a-z0-9\s]", "", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def detect_immediate_outcome(message: str) -> Outcome | None:
    normalized = normalize_message(message)

    do_not_call_phrases = (
        "do not call",
        "dont call",
        "remove me",
        "take me off",
        "stop calling",
        "do not contact",
        "dont contact",
        "unsubscribe",
    )
    if any(phrase in normalized for phrase in do_not_call_phrases):
        return Outcome.DO_NOT_CALL

    wrong_number_phrases = (
        "wrong number",
        "you have the wrong",
        "no one by that name",
        "doesnt live here",
    )
    if any(phrase in normalized for phrase in wrong_number_phrases):
        return Outcome.WRONG_NUMBER

    voicemail_phrases = (
        "this is voicemail",
        "you reached voicemail",
        "leave a message",
        "after the beep",
    )
    if any(phrase in normalized for phrase in voicemail_phrases):
        return Outcome.VOICEMAIL

    return None


def reply_for_immediate_outcome(outcome: Outcome) -> str:
    return {
        Outcome.DO_NOT_CALL: DO_NOT_CALL_REPLY,
        Outcome.WRONG_NUMBER: WRONG_NUMBER_REPLY,
        Outcome.VOICEMAIL: VOICEMAIL_REPLY,
    }[outcome]


def validate_decision(
    decision: AgentDecision,
    current_status: ConversationStatus,
) -> None:
    if current_status == ConversationStatus.ENDED:
        raise PolicyViolation("The conversation has already ended.")

    percentages = re.findall(r"(\d+(?:\.\d+)?)\s*%", decision.reply)
    if any(float(value) != DISCOUNT_PERCENT for value in percentages):
        raise PolicyViolation("The reply contains an unsupported discount.")

    written_percentages = re.findall(
        r"\b([a-z-]+)\s+percent\b",
        decision.reply,
        flags=re.IGNORECASE,
    )
    if any(value.lower() != "forty" for value in written_percentages):
        raise PolicyViolation("The reply contains an unsupported discount.")

    if re.search(r"\b(?:half|third|quarter)\s+off\b", decision.reply, re.IGNORECASE):
        raise PolicyViolation("The reply contains an unsupported discount.")

    if re.search(
        r"(?:[$€£]\s*\d)|(?:\b(?:dollars?|usd)\b)",
        decision.reply,
        flags=re.IGNORECASE,
    ):
        raise PolicyViolation("The reply contains an unsupported price estimate.")

    if re.search(
        r"\b(?:financing|payment plans?|monthly payments?|interest rates?)\b",
        decision.reply,
        flags=re.IGNORECASE,
    ):
        raise PolicyViolation("The reply contains an unsupported financing claim.")

    is_ended = decision.next_status == ConversationStatus.ENDED
    if decision.should_end != is_ended:
        raise PolicyViolation("should_end must match the next conversation status.")

    if is_ended and decision.proposed_outcome is None:
        raise PolicyViolation("An ended conversation requires a terminal outcome.")

    if not is_ended and decision.proposed_outcome is not None:
        raise PolicyViolation("An active conversation cannot have a terminal outcome.")

    if decision.proposed_outcome == Outcome.BOOKED:
        if decision.appointment_slot not in APPOINTMENT_SLOTS:
            raise PolicyViolation("A booking requires a configured appointment slot.")

    if decision.proposed_outcome == Outcome.CALLBACK:
        if not decision.callback_time or not decision.callback_time.strip():
            raise PolicyViolation("A callback requires a callback time.")

    if decision.appointment_slot and decision.proposed_outcome != Outcome.BOOKED:
        raise PolicyViolation("Only a booked outcome may set an appointment slot.")

    if decision.callback_time and decision.proposed_outcome != Outcome.CALLBACK:
        raise PolicyViolation("Only a callback outcome may set a callback time.")


def apply_decision(record: ConversationRecord, decision: AgentDecision) -> None:
    validate_decision(decision, record.status)

    record.latest_intent = decision.intent
    record.status = decision.next_status
    record.outcome = decision.proposed_outcome
    record.appointment_slot = decision.appointment_slot
    record.callback_time = decision.callback_time
    record.do_not_call = decision.proposed_outcome == Outcome.DO_NOT_CALL
    record.ended_at = (
        datetime.now(timezone.utc)
        if decision.next_status == ConversationStatus.ENDED
        else None
    )


def apply_immediate_outcome(
    record: ConversationRecord,
    outcome: Outcome,
) -> str:
    record.status = ConversationStatus.ENDED
    record.outcome = outcome
    record.latest_intent = outcome.value
    record.do_not_call = outcome == Outcome.DO_NOT_CALL
    record.ended_at = datetime.now(timezone.utc)
    return reply_for_immediate_outcome(outcome)
