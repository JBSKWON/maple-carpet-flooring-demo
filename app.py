from __future__ import annotations

import os
from html import escape

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from agent import CarpetSaleAgent
from models import ConversationStatus
from policy import (
    APPOINTMENT_SLOTS,
    DISCOUNT_PERCENT,
    SALE_PERIOD,
    STORE_NAME,
)
from state import export_record, new_conversation

load_dotenv()

CUSTOMER_NAME = "Priya"

QUICK_INPUTS = [
    ("What's included?", "What's included in the sale?"),
    ("When is it?", "When is the sale?"),
    ("How much?", "How much will it cost?"),
    ("I'm interested", "Yes, I'm interested."),
    ("Pick second slot", "The second appointment works."),
    ("Callback", "Call me tomorrow afternoon."),
    ("Not interested", "No thanks, I'm not interested."),
    ("Do not call", "I'm interested, but remove me from your list."),
    ("Wrong number", "You have the wrong number."),
    ("Voicemail", "This is voicemail. Please leave a message."),
    ("Are you AI?", "Are you an AI?"),
]


class _UnavailableResponses:
    def parse(self, **_kwargs):
        raise RuntimeError("OPENAI_API_KEY is not configured.")


class _UnavailableClient:
    def __init__(self):
        self.responses = _UnavailableResponses()


@st.cache_resource
def create_agent(api_key: str | None) -> CarpetSaleAgent:
    client = OpenAI(api_key=api_key) if api_key else _UnavailableClient()
    return CarpetSaleAgent(client)


def reset_conversation() -> None:
    st.session_state.pop("record", None)


def initialize_conversation(agent: CarpetSaleAgent) -> None:
    if "record" in st.session_state:
        return

    record = new_conversation(CUSTOMER_NAME)
    agent.start(record)
    st.session_state.record = record


def handle_message(agent: CarpetSaleAgent, message: str) -> None:
    try:
        agent.respond(st.session_state.record, message)
    except ValueError as exc:
        st.session_state.ui_error = str(exc)


st.set_page_config(
    page_title="Maple Carpet Sale Agent",
    page_icon="M",
    layout="wide",
)

st.markdown(
    """
    <style>
      :root {
        --maple: #a84c2a;
        --maple-dark: #71301d;
        --cream: #fbf6ed;
        --ink: #222722;
        --sage: #4e6b57;
      }
      .stApp {
        background:
          radial-gradient(circle at 85% 5%, rgba(168, 76, 42, 0.10), transparent 24rem),
          linear-gradient(180deg, #fffdf9 0%, var(--cream) 100%);
      }
      .block-container { padding-top: 2rem; max-width: 1180px; }
      h1, h2, h3 { color: var(--ink); }
      .eyebrow {
        color: var(--maple);
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.14em;
        text-transform: uppercase;
      }
      .hero-copy {
        color: #62655f;
        font-size: 1.02rem;
        margin-top: -0.5rem;
        max-width: 720px;
      }
      .fact-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin: 1rem 0 1.25rem;
      }
      .fact-pill {
        background: #fff;
        border: 1px solid rgba(113, 48, 29, 0.15);
        border-radius: 999px;
        box-shadow: 0 4px 16px rgba(80, 45, 30, 0.06);
        color: var(--maple-dark);
        font-size: 0.86rem;
        font-weight: 700;
        padding: 0.45rem 0.8rem;
      }
      [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(78, 107, 87, 0.12);
        border-radius: 16px;
        padding: 0.25rem 0.55rem;
      }
      [data-testid="stSidebar"] {
        background: #f4eadc;
        border-right: 1px solid rgba(113, 48, 29, 0.12);
      }
      .status-card {
        background: #fffaf2;
        border: 1px solid rgba(113, 48, 29, 0.14);
        border-radius: 14px;
        margin: 0.4rem 0;
        padding: 0.8rem 0.9rem;
      }
      .status-label {
        color: #777067;
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      .status-value {
        color: var(--ink);
        font-size: 0.95rem;
        font-weight: 750;
        margin-top: 0.2rem;
      }
      .ended-banner {
        background: #e8f1e9;
        border: 1px solid #bdd0c0;
        border-radius: 12px;
        color: #284b32;
        font-weight: 700;
        margin: 0.75rem 0;
        padding: 0.8rem 1rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

api_key = os.getenv("OPENAI_API_KEY")
agent = create_agent(api_key)
initialize_conversation(agent)
record = st.session_state.record

with st.sidebar:
    st.markdown('<div class="eyebrow">Campaign console</div>', unsafe_allow_html=True)
    st.subheader("Customer")
    st.write(f"**{record.customer_name}**")
    st.caption("Fictional returning customer")

    st.divider()
    st.subheader("Conversation status")
    status_items = [
        ("Status", record.status.value.replace("_", " ").title()),
        ("Latest intent", (record.latest_intent or "Waiting").replace("_", " ").title()),
        ("Outcome", record.outcome.value.replace("_", " ").title() if record.outcome else "Pending"),
        ("Appointment", record.appointment_slot or "Not selected"),
        ("Callback", record.callback_time or "Not requested"),
        ("Do not call", "Yes" if record.do_not_call else "No"),
    ]
    for label, value in status_items:
        safe_label = escape(label)
        safe_value = escape(str(value))
        st.markdown(
            f"""
            <div class="status-card">
              <div class="status-label">{safe_label}</div>
              <div class="status-value">{safe_value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption(f"Session: `{record.session_id}`")
    st.button("Reset conversation", use_container_width=True, on_click=reset_conversation)

    if record.status == ConversationStatus.ENDED:
        st.download_button(
            "Download result JSON",
            data=export_record(record),
            file_name=f"{record.session_id}.json",
            mime="application/json",
            use_container_width=True,
        )

st.markdown('<div class="eyebrow">Outbound text-call simulation</div>', unsafe_allow_html=True)
st.title("Maple Carpet weekend sale agent")
st.markdown(
    """
    <div class="hero-copy">
      Play the customer and test how the agent answers questions, books a free
      measure, handles rejection, and records the final call outcome.
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    f"""
    <div class="fact-row">
      <div class="fact-pill">Exactly {DISCOUNT_PERCENT}% off</div>
      <div class="fact-pill">{SALE_PERIOD.title()}</div>
      <div class="fact-pill">Free in-home measure</div>
      <div class="fact-pill">On behalf of {STORE_NAME}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not api_key:
    st.warning(
        "`OPENAI_API_KEY` is not configured. The opening and fallback safety "
        "responses work, but live conversational decisions require an API key."
    )

left, right = st.columns([1.65, 1], gap="large")

with left:
    st.subheader("Conversation")
    for message in record.transcript:
        display_role = "assistant" if message.role == "assistant" else "user"
        with st.chat_message(display_role):
            st.write(message.content)

    if record.status == ConversationStatus.ENDED:
        st.markdown(
            f'<div class="ended-banner">Conversation complete: '
            f'{record.outcome.value.replace("_", " ").title()}</div>',
            unsafe_allow_html=True,
        )

    if error := st.session_state.pop("ui_error", None):
        st.error(error)

    customer_message = st.chat_input(
        "Reply as the customer...",
        disabled=record.status == ConversationStatus.ENDED,
    )
    if customer_message:
        with st.spinner("Agent is responding..."):
            handle_message(agent, customer_message)
        st.rerun()

with right:
    st.subheader("Try a scenario")
    st.caption("Use these shortcuts to exercise the required paths.")
    for row_start in range(0, len(QUICK_INPUTS), 2):
        columns = st.columns(2)
        for offset, column in enumerate(columns):
            index = row_start + offset
            if index >= len(QUICK_INPUTS):
                continue
            label, message = QUICK_INPUTS[index]
            if column.button(
                label,
                key=f"quick-{index}",
                use_container_width=True,
                disabled=record.status == ConversationStatus.ENDED,
            ):
                with st.spinner("Agent is responding..."):
                    handle_message(agent, message)
                st.rerun()

    st.divider()
    st.subheader("Available measure times")
    for slot in APPOINTMENT_SLOTS:
        st.write(f"- {slot}")

    st.info(
        "Python owns the final booking, callback, and do-not-call state. "
        "The model proposes a structured decision; invalid actions are rejected."
    )
