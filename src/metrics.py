"""Prometheus metrics (Setup_Guide §06)."""

from __future__ import annotations

from prometheus_client import Counter, Histogram, start_http_server

TICKETS = Counter(
    "tickets_processed_total",
    "Tickets processed",
    ["channel", "outcome"],
)
LATENCY = Histogram(
    "response_seconds",
    "End to end response time",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 8, 13),
)
GUARDRAIL = Counter(
    "guardrail_blocks_total",
    "Responses blocked",
    ["guardrail"],
)
CONFIDENCE = Histogram(
    "classification_confidence",
    "Classifier confidence",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

_started = False


def start_metrics_server(port: int) -> None:
    global _started
    if _started:
        return
    start_http_server(port)
    _started = True
