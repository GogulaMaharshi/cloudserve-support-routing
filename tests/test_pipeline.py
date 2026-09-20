from src.guardrails import force_block_example
from src.pipeline import process_ticket


def test_process_does_not_drop_malformed():
    result = process_ticket({"channel": "chat", "body": ""})
    assert result["ticket_id"]
    assert result["outcome"] in {"auto_respond", "escalate", "block"}
    assert result["sent"] is True or result["escalated"] is True or result["blocked"] is True


def test_guardrail_ticket_is_blocked_or_escalated():
    result = process_ticket(force_block_example())
    assert result["outcome"] in {"block", "escalate"}
    assert result["sent"] is False


def test_same_ticket_same_route():
    raw = {
        "ticket_id": "DET-1",
        "channel": "email",
        "subject": "Rate limit 429",
        "body": "We are hitting 429 on the API. What are the per organisation limits and backoff?",
        "customer_tier": "business",
        "labels": {"intent": "rate_limit", "urgency": "medium"},
    }
    a = process_ticket(raw)
    b = process_ticket(raw)
    assert a["route"] == b["route"]
    assert a["intent"] == b["intent"]
