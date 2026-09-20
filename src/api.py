"""FastAPI application — documented in README as `python -m src.api`."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from src.config import API_HOST, API_PORT, METRICS_PORT, kill_switch_active
from src.guardrails import force_block_example
from src.logging_store import get_log
from src.metrics import start_metrics_server
from src.pipeline import process_ticket

app = FastAPI(
    title="CloudServe Support Routing System",
    description=(
        "Not a chatbot. Ingests tickets from four channels, retrieves from the "
        "knowledge base, answers only when grounded, and escalates with context."
    ),
    version="1.0.0",
)


class TicketIn(BaseModel):
    ticket_id: str | None = None
    channel: str = "email"
    subject: str | None = ""
    body: str | None = ""
    received_at: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    customer_tier: str | None = None
    customer_region: str | None = None
    language_fluency: str | None = None
    labels: dict[str, Any] | None = None
    history: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class KillSwitchIn(BaseModel):
    enabled: bool = Field(..., description="True to stop all automatic replies immediately.")


DEMO_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>CloudServe support routing</title>
  <style>
    :root { font-family: ui-sans-serif, system-ui, sans-serif; color: #102033; background: #f4f1ea; }
    body { max-width: 920px; margin: 0 auto; padding: 24px; }
    h1 { font-size: 1.4rem; margin: 0 0 8px; }
    .sub { color: #445; margin-bottom: 20px; }
    textarea, select, input, button { font: inherit; }
    textarea { width: 100%; min-height: 140px; padding: 10px; border: 1px solid #c9c2b4; border-radius: 8px; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; margin: 10px 0 16px; }
    label { display: flex; flex-direction: column; font-size: 0.85rem; gap: 4px; }
    button { background: #123; color: white; border: 0; border-radius: 8px; padding: 10px 16px; cursor: pointer; }
    button.secondary { background: #6b3; }
    pre { background: #fff; padding: 14px; border-radius: 8px; overflow: auto; border: 1px solid #ddd; }
    .out { margin-top: 16px; }
    .tag { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #dfe; font-size: 0.8rem; }
  </style>
</head>
<body>
  <h1>CloudServe support routing</h1>
  <p class="sub">This is a ticket router with retrieval, a confidence threshold, and blocking guardrails — not a chatbot. Automated replies are disclosed as automated.</p>
  <div class="row">
    <label>Channel
      <select id="channel">
        <option>email</option>
        <option>chat</option>
        <option>docs_comment</option>
        <option>forum</option>
      </select>
    </label>
    <label>Ticket id
      <input id="tid" value="DEMO-1"/>
    </label>
  </div>
  <label>Subject <input id="subject" style="width:100%;padding:8px;border:1px solid #c9c2b4;border-radius:8px" value="Deployment failing health checks"/></label>
  <p>Body</p>
  <textarea id="body">builds that work last week are now fail during dependency resolution. we are having not change our code at all.</textarea>
  <div class="row">
    <button onclick="send()">Process ticket</button>
    <button class="secondary" onclick="guard()">Trigger guardrail ticket</button>
  </div>
  <div class="out">
    <span class="tag" id="health">checking health…</span>
    <pre id="out">Submit a ticket to see ingest → classify → retrieve → route → generate → validate.</pre>
  </div>
<script>
async function send() {
  const payload = {
    ticket_id: document.getElementById('tid').value,
    channel: document.getElementById('channel').value,
    subject: document.getElementById('subject').value,
    body: document.getElementById('body').value,
    customer_name: "Demo user",
    customer_tier: "business",
    language_fluency: "non_fluent"
  };
  const res = await fetch('/tickets', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  const data = await res.json();
  document.getElementById('out').textContent = JSON.stringify(data, null, 2);
}
async function guard() {
  const res = await fetch('/demo/guardrail', {method:'POST'});
  document.getElementById('out').textContent = JSON.stringify(await res.json(), null, 2);
}
fetch('/health').then(r=>r.json()).then(j=>{
  document.getElementById('health').textContent = 'API ' + j.status + (j.kill_switch ? ' · kill switch ON' : ' · kill switch off');
});
</script>
</body>
</html>
"""


@app.on_event("startup")
def _startup() -> None:
    try:
        start_metrics_server(METRICS_PORT)
    except OSError:
        # Port already bound (tests / second worker). /metrics still works.
        pass


@app.get("/", response_class=HTMLResponse)
def demo_page() -> str:
    return DEMO_PAGE


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "kill_switch": kill_switch_active(),
        "decisions_logged": get_log().count(),
    }


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/tickets")
def submit_ticket(ticket: TicketIn) -> dict[str, Any]:
    return process_ticket(ticket.model_dump())


@app.post("/demo/guardrail")
def demo_guardrail() -> dict[str, Any]:
    """Submit the engineered ticket that must be blocked (A7)."""
    return process_ticket(force_block_example())


@app.post("/ops/kill-switch")
def set_kill_switch(body: KillSwitchIn) -> dict[str, Any]:
    from src.config import KILL_SWITCH_FILE

    if body.enabled:
        KILL_SWITCH_FILE.write_text("on\n", encoding="utf-8")
    elif KILL_SWITCH_FILE.exists():
        KILL_SWITCH_FILE.unlink()
    return {"kill_switch": kill_switch_active()}


@app.get("/decisions/{ticket_id}")
def decisions(ticket_id: str) -> dict[str, Any]:
    rows = get_log().for_ticket(ticket_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No decisions for that ticket_id")
    return {"ticket_id": ticket_id, "decisions": rows}


@app.exception_handler(Exception)
def _unhandled(_, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "outcome": "escalate",
            "sent": False,
            "error": type(exc).__name__,
            "route_reason": "Unhandled API error; ticket not dropped.",
        },
    )


def main() -> None:
    import uvicorn

    uvicorn.run("src.api:app", host=API_HOST, port=API_PORT, reload=False)


if __name__ == "__main__":
    main()
