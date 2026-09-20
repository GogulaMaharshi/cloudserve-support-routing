from src.route import route_ticket


def _cls(intent="deployment_failure", confidence=0.9, fallback=False):
    return {"intent": intent, "urgency": "high", "confidence": confidence, "fallback": fallback}


def _ticket(must_not=False):
    return {
        "ticket_id": "T",
        "labels": {"must_not_auto_respond": must_not},
        "body": "builds fail",
    }


def test_auto_when_confident_and_retrieved():
    decision = route_ticket(_ticket(), _cls(), [{"doc_id": "DOC-DEPLOY-001", "score": 0.8}])
    assert decision["action"] == "auto_respond"


def test_escalate_when_below_threshold():
    decision = route_ticket(
        _ticket(), _cls(confidence=0.1), [{"doc_id": "DOC-DEPLOY-001", "score": 0.8}]
    )
    assert decision["action"] == "escalate"
    assert "below the routing threshold" in decision["reason"]


def test_escalate_security_always():
    decision = route_ticket(
        _ticket(),
        _cls(intent="security_incident", confidence=0.99),
        [{"doc_id": "DOC-SEC-001", "score": 0.9}],
    )
    assert decision["action"] == "escalate"


def test_deterministic():
    a = route_ticket(_ticket(), _cls(), [{"doc_id": "DOC-X"}])
    b = route_ticket(_ticket(), _cls(), [{"doc_id": "DOC-X"}])
    assert a == b


def test_no_retrieval_escalates():
    decision = route_ticket(_ticket(), _cls(), [])
    assert decision["action"] == "escalate"
