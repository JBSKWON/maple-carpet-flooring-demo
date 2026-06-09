from datetime import datetime, timezone
from uuid import uuid4

from models import ConversationRecord


def new_conversation(customer_name: str) -> ConversationRecord:
    return ConversationRecord(
        session_id=f"call-{uuid4().hex[:10]}",
        customer_name=customer_name,
        started_at=datetime.now(timezone.utc),
    )


def export_record(record: ConversationRecord) -> str:
    return record.model_dump_json(indent=2)

