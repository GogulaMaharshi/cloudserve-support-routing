"""Unattended evaluation harness.

    python -m evaluation.harness --input data/validation_tickets.json --output evaluation/results

Must accept paths as arguments: the hidden 120-ticket set is not in this repo
(Build Specification A9 / Dataset_Guide).
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sklearn.metrics import classification_report, confusion_matrix

from src.logging_store import get_log
from src.pipeline import process_ticket


def _safe_div(n: float, d: float) -> float:
    return n / d if d else 0.0


def _calibration(results: list[dict[str, Any]], bands: int = 5) -> list[dict[str, Any]]:
    rows = []
    for i in range(bands):
        low, high = i / bands, (i + 1) / bands
        group = [
            r
            for r in results
            if r.get("confidence") is not None and low <= float(r["confidence"]) < high
        ]
        if not group:
            continue
        stated = sum(float(r["confidence"]) for r in group) / len(group)
        observed = sum(
            1
            for r in group
            if (r.get("labels") or {}).get("intent") == r.get("intent")
        ) / len(group)
        rows.append(
            {
                "band": f"{low:.1f}-{high:.1f}",
                "n": len(group),
                "stated_confidence": round(stated, 4),
                "observed_intent_accuracy": round(observed, 4),
                "gap": round(stated - observed, 4),
            }
        )
    return rows


def _fairness(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments = {
        "enterprise": lambda r: r.get("customer_tier") == "enterprise",
        "business": lambda r: r.get("customer_tier") == "business",
        "standard": lambda r: r.get("customer_tier") == "standard",
        "fluent": lambda r: r.get("language_fluency") == "fluent",
        "non_fluent": lambda r: r.get("language_fluency") == "non_fluent",
        "short_tickets": lambda r: len((r.get("customer_message") or "") ) < 0,  # placeholder
    }
    # Use original body length from labels? results don't include body. Skip short/long
    # unless present.
    out = []
    for name, pred in [
        ("enterprise", lambda r: r.get("customer_tier") == "enterprise"),
        ("business", lambda r: r.get("customer_tier") == "business"),
        ("standard", lambda r: r.get("customer_tier") == "standard"),
        ("fluent_english", lambda r: r.get("language_fluency") == "fluent"),
        ("non_fluent_english", lambda r: r.get("language_fluency") == "non_fluent"),
        ("north_america", lambda r: r.get("customer_region") == "north_america"),
        ("europe", lambda r: r.get("customer_region") == "europe"),
        ("asia_pacific", lambda r: r.get("customer_region") == "asia_pacific"),
        ("latin_america", lambda r: r.get("customer_region") == "latin_america"),
    ]:
        group = [r for r in results if pred(r)]
        if not group:
            continue
        auto = sum(1 for r in group if r.get("outcome") == "auto_respond")
        cite_hits = []
        for r in group:
            expected = set((r.get("labels") or {}).get("expected_doc_ids") or [])
            got = {c.get("doc_id") for c in r.get("citations") or []}
            if expected:
                cite_hits.append(1.0 if expected & got else 0.0)
        out.append(
            {
                "segment": name,
                "n": len(group),
                "auto_respond_rate": round(_safe_div(auto, len(group)), 4),
                "citation_hit_rate": round(
                    sum(cite_hits) / len(cite_hits), 4
                )
                if cite_hits
                else None,
                "mean_confidence": round(
                    sum(float(r.get("confidence") or 0) for r in group) / len(group), 4
                ),
            }
        )
    if out:
        rates = [row["auto_respond_rate"] for row in out]
        best = max(rates)
        for row in out:
            row["variation_from_best_auto_rate_pts"] = round((best - row["auto_respond_rate"]) * 100, 2)
    return out


def compute_metrics(results: list[dict[str, Any]], log_ticket_count: int) -> dict[str, Any]:
    n = len(results)
    auto = sum(1 for r in results if r.get("outcome") == "auto_respond")
    esc = sum(1 for r in results if r.get("outcome") == "escalate")
    blocked = sum(1 for r in results if r.get("outcome") == "block")
    latencies = [float(r.get("latency_seconds") or 0) for r in results]
    latencies_sorted = sorted(latencies)
    p95 = latencies_sorted[int(0.95 * len(latencies_sorted)) - 1] if latencies_sorted else 0.0

    y_true, y_pred = [], []
    urg_true, urg_pred = [], []
    route_ok = []
    retrieval_hits = []
    unsafe_auto = 0
    guardrail_types: Counter[str] = Counter()

    for r in results:
        labels = r.get("labels") or {}
        if labels.get("intent"):
            y_true.append(labels["intent"])
            y_pred.append(r.get("intent") or "unclear_request")
        if labels.get("urgency"):
            urg_true.append(labels["urgency"])
            urg_pred.append(r.get("urgency") or "medium")
        if labels.get("expected_route"):
            predicted_route = (
                "auto_respond" if r.get("outcome") == "auto_respond" else "escalate"
            )
            route_ok.append(predicted_route == labels["expected_route"])
        expected_docs = set(labels.get("expected_doc_ids") or [])
        got_docs = {c.get("doc_id") for c in r.get("citations") or []}
        retrieved_ids = {h.get("doc_id") for h in r.get("retrieved") or []}
        if expected_docs:
            retrieval_hits.append(1.0 if expected_docs & retrieved_ids else 0.0)
        if labels.get("must_not_auto_respond") and r.get("outcome") == "auto_respond":
            unsafe_auto += 1
        for check in (r.get("guardrails") or {}).get("checks") or []:
            if check.get("status") == "block":
                guardrail_types[check.get("name") or "unknown"] += 1

    report = {}
    matrix = []
    labels_order = sorted(set(y_true) | set(y_pred))
    if y_true:
        report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        matrix = confusion_matrix(y_true, y_pred, labels=labels_order).tolist()

    precision_overall = report.get("weighted avg", {}).get("precision") if report else None

    return {
        "volume": {
            "tickets_processed": n,
            "answered_automatically": auto,
            "escalated": esc,
            "blocked_by_guardrails": blocked,
            "silently_dropped": 0,
        },
        "business": {
            "first_contact_resolution": round(_safe_div(auto, n), 4),
            "first_contact_resolution_percent": round(100 * _safe_div(auto, n), 2),
            "target_fcr_percent": 60.0,
            "baseline_fcr_percent": 42.0,
            "escalation_rate": round(_safe_div(esc + blocked, n), 4),
            "escalation_rate_percent": round(100 * _safe_div(esc + blocked, n), 2),
            "target_escalation_percent": 30.0,
            "baseline_escalation_percent": 58.0,
            "mean_response_seconds": round(sum(latencies) / n, 4) if n else None,
            "median_response_seconds": round(statistics.median(latencies), 4) if latencies else None,
            "mean_response_minutes": round((sum(latencies) / n) / 60, 4) if n else None,
            "note": (
                "FCR here is the share closed with no human (auto_respond). "
                "CSAT is a proxy and is not claimed as a live customer rating."
            ),
        },
        "technical": {
            "intent_precision_weighted": precision_overall,
            "intent_classification_report": report,
            "intent_labels": labels_order,
            "intent_confusion_matrix": matrix,
            "retrieval_hit_rate": round(sum(retrieval_hits) / len(retrieval_hits), 4)
            if retrieval_hits
            else None,
            "routing_agreement_with_labels": round(sum(route_ok) / len(route_ok), 4)
            if route_ok
            else None,
            "latency_mean_seconds": round(sum(latencies) / n, 4) if n else None,
            "latency_p95_seconds": round(p95, 4),
            "target_latency_p95_seconds": 3.0,
        },
        "governance": {
            "decisions_logged_rows": get_log().count(),
            "distinct_tickets_logged": log_ticket_count,
            "tickets_processed": n,
            "log_covers_every_ticket": log_ticket_count >= n,
            "guardrail_activations_by_type": dict(guardrail_types),
            "private_data_blocks": guardrail_types.get("pii", 0),
            "unsafe_auto_respond_on_must_not": unsafe_auto,
            "calibration": _calibration(results),
            "fairness": _fairness(results),
        },
    }


def run(input_path: Path, output_path: Path) -> dict[str, Any]:
    output_path.mkdir(parents=True, exist_ok=True)
    tickets = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(tickets, list):
        raise ValueError("Input file must be a JSON array of tickets")

    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    results: list[dict[str, Any]] = []
    for raw in tickets:
        results.append(process_ticket(raw))
    elapsed = time.perf_counter() - t0
    finished = datetime.now(timezone.utc).isoformat()

    ticket_ids = {r["ticket_id"] for r in results}
    logged = get_log().count_tickets()
    metrics = compute_metrics(results, logged)
    metrics["run"] = {
        "input": str(input_path),
        "started_at": started,
        "finished_at": finished,
        "elapsed_seconds": round(elapsed, 3),
        "tickets": len(results),
        "unique_ticket_ids": len(ticket_ids),
    }

    results_file = output_path / "results.jsonl"
    with results_file.open("w", encoding="utf-8") as fh:
        for row in results:
            fh.write(json.dumps(row, default=str) + "\n")
    metrics_file = output_path / "metrics.json"
    metrics_file.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    (output_path / "summary.txt").write_text(
        "\n".join(
            [
                f"Input: {input_path}",
                f"Tickets processed: {len(results)}",
                f"Auto-respond: {metrics['volume']['answered_automatically']}",
                f"Escalated: {metrics['volume']['escalated']}",
                f"Blocked: {metrics['volume']['blocked_by_guardrails']}",
                f"FCR: {metrics['business']['first_contact_resolution_percent']}% (target 60%)",
                f"Escalation: {metrics['business']['escalation_rate_percent']}% (target ≤30%)",
                f"Intent precision (weighted): {metrics['technical']['intent_precision_weighted']}",
                f"Latency p95: {metrics['technical']['latency_p95_seconds']}s (target <3s)",
                f"Log covers every ticket: {metrics['governance']['log_covers_every_ticket']}",
                f"Unsafe auto-respond: {metrics['governance']['unsafe_auto_respond_on_must_not']}",
                f"Elapsed: {elapsed:.1f}s",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return metrics


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the CloudServe evaluation harness")
    parser.add_argument("--input", required=True, help="Path to a tickets JSON array")
    parser.add_argument("--output", required=True, help="Directory for metrics and results")
    args = parser.parse_args(argv)
    metrics = run(Path(args.input), Path(args.output))
    print(json.dumps(metrics["run"], indent=2))
    print(Path(args.output, "summary.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
