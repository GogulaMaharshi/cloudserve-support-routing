"""Runtime configuration. Secrets come from the environment, never from code."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STORAGE_DIR = ROOT / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw else default


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/llama-3.1-8b-instruct")
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

CHROMA_PATH = os.getenv("CHROMA_PATH", str(STORAGE_DIR / "chroma"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{STORAGE_DIR / 'decisions.db'}")
CLASSIFIER_PATH = Path(
    os.getenv("CLASSIFIER_PATH", str(STORAGE_DIR / "classifier.joblib"))
)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CONFIDENCE_THRESHOLD = _float("CONFIDENCE_THRESHOLD", 0.72)
RETRIEVAL_TOP_K = _int("RETRIEVAL_TOP_K", 5)
RETRIEVAL_MIN_SCORE = _float("RETRIEVAL_MIN_SCORE", 0.12)
CHUNK_SIZE = _int("CHUNK_SIZE", 800)
CHUNK_OVERLAP = _int("CHUNK_OVERLAP", 120)
# chroma (default) or lexical (TF-IDF, used in CI and as an A11 fallback)
RETRIEVAL_BACKEND = os.getenv("RETRIEVAL_BACKEND", "lexical").strip().lower()

KILL_SWITCH = _bool("KILL_SWITCH", False)
KILL_SWITCH_FILE = STORAGE_DIR / "KILL_SWITCH"

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = _int("API_PORT", 43123)
METRICS_PORT = _int("METRICS_PORT", 8001)

PROMPT_VERSION = os.getenv("PROMPT_VERSION", "PR-BUILD-03 v1.1")

# Intents that must never receive an unattended customer-facing answer.
# Source: development_tickets.json labels.must_not_auto_respond == true
# exclusively on these four classes (Dataset_Guide + measured counts).
ALWAYS_ESCALATE_INTENTS = frozenset(
    {
        "security_incident",
        "compliance_request",
        "feature_request",
        "unclear_request",
    }
)

CHANNELS = ("email", "chat", "docs_comment", "forum")
URGENCY_LEVELS = ("high", "medium", "low")


def kill_switch_active() -> bool:
    if KILL_SWITCH:
        return True
    return KILL_SWITCH_FILE.exists()


def llm_configured() -> bool:
    return bool(OPENROUTER_API_KEY)
