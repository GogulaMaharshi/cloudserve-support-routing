from src.ingest import ingest_ticket


def test_four_channels_normalise():
    for channel in ("email", "chat", "docs_comment", "forum"):
        t = ingest_ticket(
            {
                "ticket_id": f"T-{channel}",
                "channel": channel,
                "subject": "Subject" if channel != "chat" else "",
                "body": "Cannot deploy after last week's change.",
            }
        )
        assert t["channel"] == channel
        assert t["body"]
        assert "text" in t


def test_missing_fields_do_not_raise():
    t = ingest_ticket({})
    assert t["ticket_id"] == "UNK-MISSING-ID"
    assert "missing_ticket_id" in t["ingest_warnings"]
    assert t["channel"] == "email"


def test_non_object_payload():
    t = ingest_ticket("not-json")
    assert t["ingest_warnings"]
    assert t["channel"] in {"email", "chat", "docs_comment", "forum"}


def test_preserves_original_and_channel():
    raw = {
        "ticket_id": "DEV-1",
        "channel": "forum",
        "subject": "key rotation",
        "body": "401 on prod key",
        "extra_field": "keep-me",
    }
    t = ingest_ticket(raw)
    assert t["channel"] == "forum"
    assert t["raw"]["extra_field"] == "keep-me"
    assert t["subject"] == "key rotation"
