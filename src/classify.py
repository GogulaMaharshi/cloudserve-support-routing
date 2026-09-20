"""Intent and urgency classification with calibrated confidence.

Deterministic given the trained sklearn model (A5 input). Falls back to
unclear_request / medium / confidence 0.0 instead of raising (A3, A11).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

from src.config import ALWAYS_ESCALATE_INTENTS, CLASSIFIER_PATH, DATA_DIR, URGENCY_LEVELS

FALLBACK_INTENT = "unclear_request"
FALLBACK_URGENCY = "medium"


def _text(ticket: dict[str, Any]) -> str:
    return ticket.get("text") or f"{ticket.get('subject', '')}\n{ticket.get('body', '')}"


def _build_pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=25000,
                    strip_accents="unicode",
                ),
            ),
            (
                "clf",
                CalibratedClassifierCV(
                    LogisticRegression(max_iter=400, C=2.0, class_weight="balanced"),
                    cv=3,
                    method="sigmoid",
                ),
            ),
        ]
    )


def train_classifier(
    tickets_path: Path | None = None, output_path: Path | None = None
) -> Path:
    tickets_path = tickets_path or (DATA_DIR / "development_tickets.json")
    output_path = output_path or CLASSIFIER_PATH
    tickets = json.loads(tickets_path.read_text(encoding="utf-8"))
    texts = []
    intents = []
    urgencies = []
    for t in tickets:
        labels = t.get("labels") or {}
        intent = labels.get("intent")
        urgency = labels.get("urgency")
        if not intent or not urgency:
            continue
        texts.append(f"{t.get('subject', '')}\n{t.get('body', '')}")
        intents.append(intent)
        urgencies.append(urgency)

    intent_pipe = _build_pipeline()
    intent_pipe.fit(texts, intents)

    urgency_le = LabelEncoder()
    y_urg = urgency_le.fit_transform(urgencies)
    urg_pipe = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=15000,
                ),
            ),
            (
                "clf",
                OneVsRestClassifier(
                    LogisticRegression(max_iter=400, C=2.0, class_weight="balanced")
                ),
            ),
        ]
    )
    urg_pipe.fit(texts, y_urg)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "intent": intent_pipe,
            "urgency": urg_pipe,
            "urgency_labels": list(urgency_le.classes_),
            "always_escalate": sorted(ALWAYS_ESCALATE_INTENTS),
        },
        output_path,
    )
    return output_path


class Classifier:
    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path or CLASSIFIER_PATH
        self._bundle: dict[str, Any] | None = None

    def load(self) -> None:
        if self._bundle is None:
            if not self.model_path.exists():
                train_classifier(output_path=self.model_path)
            self._bundle = joblib.load(self.model_path)

    def classify(self, ticket: dict[str, Any]) -> dict[str, Any]:
        try:
            self.load()
            text = _text(ticket)
            if not text.strip():
                return self._fallback("empty_text")

            intent_pipe = self._bundle["intent"]
            classes = list(intent_pipe.classes_)
            proba = intent_pipe.predict_proba([text])[0]
            ranked = sorted(zip(classes, proba), key=lambda x: x[1], reverse=True)
            intent, confidence = ranked[0]
            alternatives = [
                {"value": name, "confidence": round(float(p), 4)} for name, p in ranked[:4]
            ]

            urg_pipe = self._bundle["urgency"]
            urg_labels = self._bundle["urgency_labels"]
            urg_proba = urg_pipe.predict_proba([text])[0]
            urg_ranked = sorted(
                zip(urg_labels, urg_proba), key=lambda x: x[1], reverse=True
            )
            urgency = urg_ranked[0][0]
            if urgency not in URGENCY_LEVELS:
                urgency = FALLBACK_URGENCY

            return {
                "intent": intent,
                "urgency": urgency,
                "confidence": float(confidence),
                "alternatives": alternatives,
                "urgency_alternatives": [
                    {"value": n, "confidence": round(float(p), 4)} for n, p in urg_ranked
                ],
                "fallback": False,
                "reason": "calibrated_logistic_regression",
            }
        except Exception as exc:  # noqa: BLE001 — A11: never crash classification
            return self._fallback(f"classifier_error:{type(exc).__name__}")

    def _fallback(self, reason: str) -> dict[str, Any]:
        return {
            "intent": FALLBACK_INTENT,
            "urgency": FALLBACK_URGENCY,
            "confidence": 0.0,
            "alternatives": [{"value": FALLBACK_INTENT, "confidence": 0.0}],
            "urgency_alternatives": [{"value": FALLBACK_URGENCY, "confidence": 0.0}],
            "fallback": True,
            "reason": reason,
        }


_default: Classifier | None = None


def get_classifier() -> Classifier:
    global _default
    if _default is None:
        _default = Classifier()
    return _default


def classify_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
    return get_classifier().classify(ticket)
