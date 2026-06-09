from __future__ import annotations

from datetime import datetime, timezone

from models import AgentDecision, ConversationRecord, ConversationStatus, Message
from policy import (
    APPOINTMENT_SLOTS,
    APPOINTMENT_TYPE,
    DISCOUNT_PERCENT,
    SAFE_FALLBACK_REPLY,
    SALE_PERIOD,
    STORE_NAME,
    apply_decision,
    apply_immediate_outcome,
    detect_immediate_outcome,
)

MODEL = "gpt-4o-mini"

OPENING_REQUEST = (
    "Begin the outbound conversation now. Introduce yourself as Maya, an AI "
    "assistant calling on behalf of the store, briefly state the confirmed sale, "
    "and ask whether a free in-home measure would be useful."
)


def build_instructions(record: ConversationRecord) -> str:
    slots = "\n".join(f"- {slot}" for slot in APPOINTMENT_SLOTS)
    return f"""
You are Maya, a concise, respectful AI sales assistant calling on behalf of
{STORE_NAME}. This is a text simulation of an outbound call.

Confirmed campaign facts:
- The discount is exactly {DISCOUNT_PERCENT}%.
- The sale is {SALE_PERIOD}.
- The appointment is a {APPOINTMENT_TYPE}.
- Available appointments are:
{slots}

Current local conversation status: {record.status.value}

Behavior:
- Keep replies natural and normally one or two short sentences.
- Answer the customer's question before asking at most one follow-up question.
- Guide interested customers toward a free in-home measure.
- If they are interested but do not want an appointment, capture interested.
- If they request a callback without a time, use awaiting_callback_time.
- If they provide callback timing, end with callback and copy their timing.
- If they select an appointment, use only an exact available slot.
- If they decline, end with not_interested and do not continue selling.
- If this is a wrong number, end with wrong_number.
- If this is voicemail, leave one brief factual message and end with voicemail.
- If they request no further contact, end with do_not_call.
- If asked whether you are AI, answer yes directly.
- Never invent prices, estimates, product eligibility, exclusions, financing,
  warranties, installation terms, store hours, or additional discounts.
- For unknown details, say the store must confirm them.

Return an AgentDecision. The reply field is the exact customer-facing message.
For non-ended turns, proposed_outcome must be null. For ended turns, provide
exactly one outcome and set should_end to true.
""".strip()


class CarpetSaleAgent:
    def __init__(self, client):
        self.client = client

    def start(self, record: ConversationRecord) -> str:
        if record.transcript or record.previous_response_id:
            raise ValueError("The conversation has already started.")

        try:
            api_response = self.client.responses.parse(
                model=MODEL,
                instructions=build_instructions(record),
                input=OPENING_REQUEST,
                text_format=AgentDecision,
            )
            decision = self._parsed_decision(api_response)
            apply_decision(record, decision)
        except Exception:
            reply = (
                f"Hi {record.customer_name}, I'm Maya, an AI assistant calling "
                f"on behalf of {STORE_NAME}. We're offering exactly "
                f"{DISCOUNT_PERCENT}% off {SALE_PERIOD}; would a free in-home "
                "measure be useful?"
            )
            self._append(record, "assistant", reply)
            return reply

        record.previous_response_id = api_response.id
        self._append(record, "assistant", decision.reply)
        return decision.reply

    def respond(self, record: ConversationRecord, customer_message: str) -> str:
        if record.status == ConversationStatus.ENDED:
            raise ValueError("The conversation has already ended.")
        if not customer_message.strip():
            raise ValueError("Customer message cannot be empty.")

        self._append(record, "customer", customer_message.strip())

        immediate_outcome = detect_immediate_outcome(customer_message)
        if immediate_outcome is not None:
            reply = apply_immediate_outcome(record, immediate_outcome)
            self._append(record, "assistant", reply)
            return reply

        request = {
            "model": MODEL,
            "instructions": build_instructions(record),
            "input": customer_message.strip(),
            "text_format": AgentDecision,
        }
        if record.previous_response_id:
            request["previous_response_id"] = record.previous_response_id

        try:
            api_response = self.client.responses.parse(**request)
            decision = self._parsed_decision(api_response)
            apply_decision(record, decision)
        except Exception:
            self._append(record, "assistant", SAFE_FALLBACK_REPLY)
            return SAFE_FALLBACK_REPLY

        record.previous_response_id = api_response.id
        self._append(record, "assistant", decision.reply)
        return decision.reply

    @staticmethod
    def _parsed_decision(api_response) -> AgentDecision:
        decision = api_response.output_parsed
        if decision is None:
            raise ValueError("The model did not return a structured decision.")
        return decision

    @staticmethod
    def _append(
        record: ConversationRecord,
        role: str,
        content: str,
    ) -> None:
        record.transcript.append(
            Message(
                role=role,
                content=content,
                timestamp=datetime.now(timezone.utc),
            )
        )
