"""End-to-end pipeline orchestrated with LangGraph.

Six nodes match Project Brief §04: ingest, classify, retrieve, route,
generate, validate. One ticket in → one outcome out; never dropped (A9).
"""

from __future__ import annotations

import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.classify import classify_ticket
from src.config import PROMPT_VERSION
from src.generate import generate_answer
from src.guardrails import validate_response
from src.ingest import ingest_ticket
from src.logging_store import get_log
from src.metrics import CONFIDENCE, GUARDRAIL, LATENCY, TICKETS
from src.retrieve import retrieve
from src.route import AUTO, ESCALATE, route_ticket


class TicketState(TypedDict, total=False):
    raw: dict[str, Any]
    ticket: dict[str, Any]
    classification: dict[str, Any]
    retrieved: list[dict[str, Any]]
    routing: dict[str, Any]
    draft: dict[str, Any]
    validation: dict[str, Any]
    result: dict[str, Any]


def _node_ingest(state: TicketState) -> TicketState:
    ticket = ingest_ticket(state.get("raw") or {})
    return {"ticket": ticket}


def _node_classify(state: TicketState) -> TicketState:
    classification = classify_ticket(state["ticket"])
    CONFIDENCE.observe(float(classification.get("confidence") or 0.0))
    get_log().record(
        ticket_id=state["ticket"]["ticket_id"],
        stage="classification",
        action_taken="classify",
        reason=classification.get("reason") or "classified",
        prediction={
            "intent": classification.get("intent"),
            "urgency": classification.get("urgency"),
        },
        confidence=classification.get("confidence"),
        payload={"alternatives": classification.get("alternatives")},
        requirement_ids=["FR-02", "FR-03"],
    )
    return {"classification": classification}


def _node_retrieve(state: TicketState) -> TicketState:
    ticket = state["ticket"]
    hits = retrieve(ticket.get("text") or ticket.get("body") or "")
    get_log().record(
        ticket_id=ticket["ticket_id"],
        stage="retrieval",
        action_taken="retrieve",
        reason=f"{len(hits)} passage(s) above the relevance threshold.",
        sources_used=hits,
        requirement_ids=["FR-04"],
    )
    return {"retrieved": hits}


def _node_route(state: TicketState) -> TicketState:
    routing = route_ticket(
        state["ticket"], state["classification"], state.get("retrieved") or []
    )
    get_log().record(
        ticket_id=state["ticket"]["ticket_id"],
        stage="routing",
        action_taken=routing["action"],
        reason=routing["reason"],
        prediction=routing.get("intent"),
        confidence=routing.get("confidence"),
        threshold=routing.get("threshold"),
        sources_used=routing.get("source_ids"),
        requirement_ids=["FR-05"],
    )
    return {"routing": routing}


def _node_generate(state: TicketState) -> TicketState:
    draft = generate_answer(
        state["ticket"], state["classification"], state.get("retrieved") or []
    )
    get_log().record(
        ticket_id=state["ticket"]["ticket_id"],
        stage="generation",
        action_taken="draft",
        reason="Draft produced" if not draft.get("unknown") else "Draft states unknown",
        sources_used=draft.get("citations"),
        prompt_version=draft.get("prompt_version") or PROMPT_VERSION,
        requirement_ids=["FR-06"],
        payload={"generator": draft.get("generator")},
    )
    return {"draft": draft}


def _node_validate(state: TicketState) -> TicketState:
    routing = state["routing"]
    draft = state.get("draft") or {
        "message": "",
        "citations": [],
        "unknown": True,
    }
    apply_floor = routing.get("action") == AUTO
    validation = validate_response(
        state["ticket"],
        state["classification"],
        state.get("retrieved") or [],
        draft,
        apply_confidence_floor=apply_floor,
    )
    for check in validation.get("checks") or []:
        if check.get("status") == "block":
            GUARDRAIL.labels(guardrail=check.get("name") or "unknown").inc()

    get_log().record(
        ticket_id=state["ticket"]["ticket_id"],
        stage="validation",
        action_taken=validation["action"],
        reason=validation["reason"],
        guardrails=validation.get("checks"),
        prompt_version=PROMPT_VERSION,
        requirement_ids=["FR-07", "FR-08"],
    )
    return {"validation": validation}


def _assemble(ticket, classification, retrieved, routing, draft, validation, elapsed) -> dict[str, Any]:
    if validation.get("blocked"):
        outcome = "block"
        send = False
        customer_message = None
        escalation_packet = {
            "summary": draft.get("message") if draft else None,
            "why_blocked": validation.get("reason"),
            "sources": retrieved,
            "classification": classification,
        }
    elif routing.get("action") == ESCALATE or (draft and draft.get("unknown")):
        outcome = "escalate"
        send = False
        customer_message = None
        escalation_packet = {
            "summary": (
                f"Predicted {classification.get('intent')} "
                f"({classification.get('urgency')}, "
                f"confidence {float(classification.get('confidence') or 0):.2f})."
            ),
            "uncertainty": routing.get("reason"),
            "draft": draft.get("message") if draft else None,
            "sources": retrieved,
            "classification": classification,
        }
        if draft and draft.get("unknown") and routing.get("action") == AUTO:
            outcome = "escalate"
    else:
        outcome = "auto_respond"
        send = True
        customer_message = draft.get("message") if draft else ""
        escalation_packet = None

    return {
        "ticket_id": ticket["ticket_id"],
        "channel": ticket.get("channel"),
        "customer_tier": ticket.get("customer_tier"),
        "customer_region": ticket.get("customer_region"),
        "language_fluency": ticket.get("language_fluency"),
        "intent": classification.get("intent"),
        "urgency": classification.get("urgency"),
        "confidence": classification.get("confidence"),
        "alternatives": classification.get("alternatives"),
        "retrieved": retrieved,
        "route": routing.get("action"),
        "route_reason": routing.get("reason"),
        "threshold": routing.get("threshold"),
        "outcome": outcome,
        "sent": send,
        "customer_message": customer_message,
        "citations": (draft or {}).get("citations") or [],
        "escalation": escalation_packet,
        "guardrails": validation,
        "latency_seconds": elapsed,
        "generator": (draft or {}).get("generator"),
        "labels": ticket.get("labels") or {},
        "ingest_warnings": ticket.get("ingest_warnings") or [],
        "closed_without_human": outcome == "auto_respond",
        "escalated": outcome in {"escalate", "block"},
        "blocked": outcome == "block",
    }


def build_graph():
    graph = StateGraph(TicketState)
    graph.add_node("ingest", _node_ingest)
    graph.add_node("classify", _node_classify)
    graph.add_node("retrieve", _node_retrieve)
    graph.add_node("route", _node_route)
    graph.add_node("generate", _node_generate)
    graph.add_node("validate", _node_validate)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "route")
    graph.add_edge("route", "generate")
    graph.add_edge("generate", "validate")
    graph.add_edge("validate", END)
    return graph.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def process_ticket(raw: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        final = get_graph().invoke({"raw": raw})
        elapsed = time.perf_counter() - started
        result = _assemble(
            final["ticket"],
            final["classification"],
            final.get("retrieved") or [],
            final["routing"],
            final.get("draft"),
            final.get("validation") or {"blocked": False, "action": "pass", "reason": "", "checks": []},
            elapsed,
        )
    except Exception as exc:  # noqa: BLE001 — A11: degrade and continue
        elapsed = time.perf_counter() - started
        ticket = ingest_ticket(raw)
        result = {
            "ticket_id": ticket.get("ticket_id") or "UNK",
            "channel": ticket.get("channel"),
            "customer_tier": ticket.get("customer_tier"),
            "customer_region": ticket.get("customer_region"),
            "language_fluency": ticket.get("language_fluency"),
            "intent": "unclear_request",
            "urgency": "medium",
            "confidence": 0.0,
            "alternatives": [],
            "retrieved": [],
            "route": ESCALATE,
            "route_reason": f"Pipeline error {type(exc).__name__}: ticket escalated rather than dropped.",
            "threshold": None,
            "outcome": "escalate",
            "sent": False,
            "customer_message": None,
            "citations": [],
            "escalation": {"summary": f"Unhandled error {type(exc).__name__}", "sources": []},
            "guardrails": {"blocked": False, "action": "pass", "checks": [], "reason": "error_path"},
            "latency_seconds": elapsed,
            "generator": None,
            "labels": ticket.get("labels") or {},
            "ingest_warnings": ticket.get("ingest_warnings") or [],
            "closed_without_human": False,
            "escalated": True,
            "blocked": False,
            "error": type(exc).__name__,
        }
        get_log().record(
            ticket_id=result["ticket_id"],
            stage="pipeline",
            action_taken="escalate",
            reason=result["route_reason"],
            requirement_ids=["NFR-02"],
        )

    TICKETS.labels(
        channel=result.get("channel") or "unknown",
        outcome=result.get("outcome") or "unknown",
    ).inc()
    LATENCY.observe(result.get("latency_seconds") or 0.0)

    get_log().record(
        ticket_id=result["ticket_id"],
        stage="pipeline",
        action_taken=result["outcome"],
        reason=result.get("route_reason") or result["outcome"],
        prediction=result.get("intent"),
        confidence=result.get("confidence"),
        threshold=result.get("threshold"),
        sources_used=[c.get("doc_id") for c in result.get("citations") or []],
        guardrails=(result.get("guardrails") or {}).get("checks"),
        prompt_version=PROMPT_VERSION,
        requirement_ids=["FR-01"],
        payload={"latency_seconds": result.get("latency_seconds")},
    )
    return result
