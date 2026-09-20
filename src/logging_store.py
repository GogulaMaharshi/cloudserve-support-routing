"""Persistent decision log. Every automated decision is reconstructable (A8)."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import DATABASE_URL, STORAGE_DIR

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS decisions (
    decision_id     TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    ticket_id       TEXT NOT NULL,
    stage           TEXT NOT NULL,
    prediction      TEXT,
    confidence      REAL,
    threshold       REAL,
    action_taken    TEXT NOT NULL,
    reason          TEXT NOT NULL,
    sources_used    TEXT,
    guardrails      TEXT,
    prompt_version  TEXT,
    requirement_ids TEXT,
    payload         TEXT
)
"""


def _sqlite_path() -> Path:
    # sqlite:///./storage/decisions.db
    raw = DATABASE_URL
    if raw.startswith("sqlite:///"):
        path = raw.replace("sqlite:///", "", 1)
        return Path(path)
    return STORAGE_DIR / "decisions.db"


class DecisionLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _sqlite_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure(self) -> None:
        with self._connect() as conn:
            conn.execute(CREATE_SQL)
            conn.commit()

    def record(
        self,
        *,
        ticket_id: str,
        stage: str,
        action_taken: str,
        reason: str,
        prediction: Any = None,
        confidence: float | None = None,
        threshold: float | None = None,
        sources_used: Any = None,
        guardrails: Any = None,
        prompt_version: str | None = None,
        requirement_ids: list[str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        decision_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO decisions (
                    decision_id, created_at, ticket_id, stage, prediction,
                    confidence, threshold, action_taken, reason, sources_used,
                    guardrails, prompt_version, requirement_ids, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    created_at,
                    ticket_id,
                    stage,
                    json.dumps(prediction) if prediction is not None else None,
                    confidence,
                    threshold,
                    action_taken,
                    reason,
                    json.dumps(sources_used) if sources_used is not None else None,
                    json.dumps(guardrails) if guardrails is not None else None,
                    prompt_version,
                    json.dumps(requirement_ids or []),
                    json.dumps(payload or {}),
                ),
            )
            conn.commit()
        return decision_id

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0])

    def count_tickets(self) -> int:
        with self._connect() as conn:
            return int(
                conn.execute("SELECT COUNT(DISTINCT ticket_id) FROM decisions").fetchone()[0]
            )

    def for_ticket(self, ticket_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE ticket_id = ? ORDER BY created_at",
                (ticket_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def export_rows(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM decisions ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]


_log: DecisionLog | None = None


def get_log() -> DecisionLog:
    global _log
    if _log is None:
        _log = DecisionLog()
    return _log
