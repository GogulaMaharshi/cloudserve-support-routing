"""Normalise tickets from email, chat, docs_comment, and forum into one shape.

Build Specification §03 Ingest and A2. Channel quirks stay in `channel` and
`raw`; they must not leak into downstream field names.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.config import CHANNELS

VALID_CHANNELS = set(CHANNELS)

NORMALIZED_FIELDS = (
    "ticket_id",
    "channel",
    "subject",
    "body",
    "text",
    "received_at",
    "customer_id",
    "customer_name",
    "customer_tier",
    "customer_region",
    "language_fluency",
    "labels",
    "history",
    "raw",
    "ingest_warnings",
)


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _parse_received_at(value: Any) -> str:
    text = _as_str(value).strip()
    if not text:
        return datetime.now(timezone.utc).isoformat()
    try:
        cleaned = text.replace("Z", "+00:00")
        datetime.fromisoformat(cleaned)
        return text
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def ingest_ticket(raw: Any) -> dict[str, Any]:
    """Return one internal representation. Never raises on malformed input (A11)."""
    warnings: list[str] = []
    if raw is None or not isinstance(raw, dict):
        warnings.append("payload_not_object")
        raw = {}

    channel = _as_str(raw.get("channel")).strip().lower() or "email"
    if channel not in VALID_CHANNELS:
        warnings.append(f"unknown_channel:{channel}")
        aliases = {
            "live_chat": "chat",
            "livechat": "chat",
            "documentation": "docs_comment",
            "docs": "docs_comment",
            "comment": "docs_comment",
            "community": "forum",
        }
        channel = aliases.get(channel, "email")

    ticket_id = _as_str(raw.get("ticket_id")).strip()
    if not ticket_id:
        ticket_id = "UNK-MISSING-ID"
        warnings.append("missing_ticket_id")

    subject = _as_str(raw.get("subject"))
    body = _as_str(raw.get("body"))
    if not body.strip():
        warnings.append("empty_body")
    # Chat tickets in development_tickets.json have empty subjects (measured).
    text = "\n".join(part for part in (subject.strip(), body) if part).strip()

    labels = raw.get("labels") if isinstance(raw.get("labels"), dict) else {}
    history = raw.get("history") if isinstance(raw.get("history"), dict) else {}

    return {
        "ticket_id": ticket_id,
        "channel": channel,
        "subject": subject,
        "body": body,
        "text": text,
        "received_at": _parse_received_at(raw.get("received_at")),
        "customer_id": _as_str(raw.get("customer_id")),
        "customer_name": _as_str(raw.get("customer_name")),
        "customer_tier": _as_str(raw.get("customer_tier")) or "unknown",
        "customer_region": _as_str(raw.get("customer_region")) or "unknown",
        "language_fluency": _as_str(raw.get("language_fluency")) or "unknown",
        "labels": labels,
        "history": history,
        "raw": raw,
        "ingest_warnings": warnings,
    }


def ingest_many(tickets: list[Any]) -> list[dict[str, Any]]:
    return [ingest_ticket(t) for t in tickets]
