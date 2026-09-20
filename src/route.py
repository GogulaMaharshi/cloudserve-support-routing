"""Routing: auto-respond vs escalate. Deterministic for a given ticket state (A5).

Threshold was chosen on development_tickets.json (see docs/architecture.md).
CONFIDENCE_THRESHOLD in .env is the measured value, not the 0.80 illustration
in the Project Brief figure.
"""

from __future__ import annotations

from typing import Any

from src.config import ALWAYS_ESCALATE_INTENTS, CONFIDENCE_THRESHOLD, kill_switch_active

AUTO = "auto_respond"
ESCALATE = "escalate"


def route_ticket(
    ticket: dict[str, Any],
    classification: dict[str, Any],
    retrieved: list[dict[str, Any]],
    threshold: float | None = None,
) -> dict[str, Any]:
    threshold = CONFIDENCE_THRESHOLD if threshold is None else threshold
    intent = classification.get("intent") or "unclear_request"
    confidence = float(classification.get("confidence") or 0.0)
    labels = ticket.get("labels") or {}

    reasons: list[str] = []
    action = AUTO

    if kill_switch_active():
        action = ESCALATE
        reasons.append("Kill switch is on: automatic replies are disabled.")

    # Safety classes measured from labels.must_not_auto_respond.
    if intent in ALWAYS_ESCALATE_INTENTS or labels.get("must_not_auto_respond"):
        action = ESCALATE
        reasons.append(
            f"Intent '{intent}' is in the always-escalate set "
            "(security, compliance, feature request, or unclear)."
        )

    if classification.get("fallback"):
        action = ESCALATE
        reasons.append(
            "The classifier could not produce a reliable label, so the ticket is handed to an agent."
        )

    if confidence < threshold:
        action = ESCALATE
        reasons.append(
            f"Classifier confidence {confidence:.2f} is below the routing threshold {threshold:.2f}."
        )

    if not retrieved:
        action = ESCALATE
        reasons.append(
            "No documentation passage passed the relevance threshold, so there is nothing to ground an answer on."
        )

    if action == AUTO and not reasons:
        reasons.append(
            f"Intent '{intent}' is answerable from retrieved documentation "
            f"(confidence {confidence:.2f} ≥ {threshold:.2f})."
        )

    return {
        "action": action,
        "threshold": threshold,
        "reason": " ".join(reasons),
        "intent": intent,
        "confidence": confidence,
        "source_count": len(retrieved),
        "source_ids": [r.get("doc_id") for r in retrieved],
    }
