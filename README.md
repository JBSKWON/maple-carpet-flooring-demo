# Maple Carpet Weekend Sale Agent

A text-based outbound-call simulation for Maple Carpet & Flooring. The
prototype uses Streamlit and OpenAI's Responses API to hold a natural
multi-turn conversation, while Python owns the campaign policy and final call
outcome.

## What It Demonstrates

- Identifies itself as an AI calling on behalf of Maple Carpet & Flooring.
- Shares exactly 40% off, this weekend only.
- Guides interested customers toward a free in-home measure.
- Handles questions about inclusions, timing, cost, and AI identity.
- Handles callbacks, rejection, wrong numbers, voicemail, and do-not-call.
- Captures `booked`, `interested`, `callback`, `not_interested`,
  `do_not_call`, `wrong_number`, or `voicemail`.
- Exports the complete result and transcript as JSON.

## Link to the app
You can try running the link below:
https://jbskwon-maple-carpet-flooring-demo-app-zauw3f.streamlit.app/

## Architecture

```text
Customer message
    |
    v
Immediate do-not-call / wrong-number / voicemail detection
    |
    v
gpt-4o-mini through the Responses API
    |
    v
Pydantic AgentDecision
    |
    v
Python policy and transition validation
    |
    v
ConversationRecord + Streamlit UI + JSON export
```

The latest OpenAI response ID is supplied as `previous_response_id` on the next
turn. This gives the model conversational context for follow-ups such as "the
second one." Campaign instructions are supplied on every request because
instructions are not inherited through a response chain.

## Safety Boundary

The model proposes a reply and state transition; it does not directly modify
the customer record.

Python enforces:

- Do-not-call before any model request.
- Exactly 40% as the only permitted percentage.
- No dollar estimates.
- Exact matching against the configured appointment slots.
- Callback outcomes with callback timing.
- One terminal outcome for every ended conversation.
- No additional turns after termination.

If an API call or model decision fails validation, the response chain and
business state do not advance. The customer receives a short, factual fallback.

## Demo Data

The prototype uses fictional customer data and these measure slots:

- Saturday at 10:00 AM
- Saturday at 2:00 PM
- Sunday at 11:00 AM

It does not claim product eligibility, exclusions, project pricing, financing,
warranties, installation terms, or store hours.

## Main Files

- `app.py`: Streamlit interface and session lifecycle.
- `agent.py`: Responses API calls, repeated instructions, and turn handling.
- `models.py`: Pydantic conversation and decision models.
- `policy.py`: fixed campaign facts, immediate outcomes, and validators.
- `state.py`: fresh-session creation and JSON export.

## Production Follow-Up

The next step would connect the same policy and outcome layer to telephony and
a real scheduling system, then persist consent and do-not-call status in a CRM.
Production deployment would also require legal review, calling-hour controls,
customer-list authorization, secure storage, and monitoring.

