import json
from pathlib import Path

from evaluation.harness import main


def test_harness_requires_paths(tmp_path, capsys):
    tickets = [
        {
            "ticket_id": "H-1",
            "channel": "email",
            "subject": "login fails",
            "body": "invalid credentials after password change",
            "customer_tier": "standard",
            "customer_region": "europe",
            "language_fluency": "fluent",
            "labels": {
                "intent": "authentication_failure",
                "urgency": "high",
                "expected_route": "auto_respond",
                "answerable_from_docs": True,
                "expected_doc_ids": ["DOC-AUTH-001"],
                "must_not_auto_respond": False,
            },
        }
    ]
    src = tmp_path / "in.json"
    src.write_text(json.dumps(tickets), encoding="utf-8")
    out = tmp_path / "out"
    main(["--input", str(src), "--output", str(out)])
    assert (out / "metrics.json").exists()
    assert (out / "results.jsonl").exists()
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["volume"]["tickets_processed"] == 1
    assert metrics["volume"]["silently_dropped"] == 0
