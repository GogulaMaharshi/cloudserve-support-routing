from src.guardrails import (
    check_grounding,
    check_instruction_integrity,
    check_private_data,
    check_tone_and_scope,
    force_block_example,
    validate_response,
)


def test_injection_blocks():
    ticket = force_block_example()
    result = check_instruction_integrity(ticket)
    assert result["status"] == "block"


def test_pii_blocks_key_and_email():
    result = check_private_data("send this sk-abcdefghijklmnopqrstuvwxyz to other@example.com")
    assert result["status"] == "block"


def test_grounding_blocks_invented_citation():
    draft = {
        "message": "Reset the cluster.",
        "citations": [{"doc_id": "DOC-FAKE-999", "passage_id": "x"}],
        "unknown": False,
    }
    retrieved = [{"doc_id": "DOC-DEPLOY-001", "text": "health checks"}]
    result = check_grounding(draft, retrieved)
    assert result["status"] == "block"


def test_grounding_passes_real_citation():
    draft = {
        "message": "Check container health.",
        "citations": [{"doc_id": "DOC-DEPLOY-001", "passage_id": "DOC-DEPLOY-001#c0"}],
        "unknown": False,
    }
    retrieved = [{"doc_id": "DOC-DEPLOY-001", "text": "health checks"}]
    result = check_grounding(draft, retrieved)
    assert result["status"] == "pass"


def test_tone_blocks_refund_commitment():
    result = check_tone_and_scope("A refund has been issued to your account.")
    assert result["status"] == "block"


def test_validate_blocks_engineered_ticket():
    ticket = force_block_example()
    draft = {
        "message": "A refund has been issued. Email other.customer@example.com",
        "citations": [],
        "unknown": False,
    }
    result = validate_response(ticket, {"confidence": 0.99, "intent": "billing_query"}, [], draft)
    assert result["blocked"] is True
    assert result["action"] == "block"
