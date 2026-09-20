# CloudServe Support Routing System

Individual capstone for Forward Deployed AI Engineering. CloudServe asked for a **chatbot**. This repository is **not** a chatbot. It is a ticket router that retrieves from CloudServe's own knowledge base, answers only when the answer is grounded, and escalates everything else with a draft, sources, and a human-readable reason.

Author: Maharshi Gogula.

## What this system does

1. Ingests tickets from `email`, `chat`, `docs_comment`, and `forum`.
2. Classifies intent and urgency with a calibrated model and a numeric confidence.
3. Retrieves passages from `data/documentation.json`.
4. Routes to `auto_respond` or `escalate` using a threshold measured on development data.
5. Drafts a cited reply (OpenRouter if a key is present; otherwise extractive grounding).
6. Runs **blocking** guardrails (private data, grounding, injection, commitments).
7. Writes every decision to SQLite.
8. Emits a metrics report from a single unattended command.

The client outcome this is built for: fewer tickets need a human, the ones that do arrive with context, and customers stop waiting half a day for an answer that already existed in the documentation (`01_Project_Brief.docx` §02).

## Requirements

- Python 3.10 or later (developed on 3.12)
- About 1 GB of disk for the environment
- Optional: an OpenRouter API key (free tier). The system runs without it.

## Setup (clean checkout)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env if you have OPENROUTER_API_KEY. Leave it empty to use the offline generator.
```

Optional neural embeddings (Project Brief stack: Chroma + `all-MiniLM-L6-v2`):

```bash
python -m pip install -r requirements-embeddings.txt
# then set RETRIEVAL_BACKEND=chroma in .env
```

Default in this checkout is `RETRIEVAL_BACKEND=lexical` (TF-IDF over the same corpus). That backend satisfies A4 (identifiable `doc_id` passages) and A11 (no crash if the embedding model cannot download). Record which backend you used in any evaluation you report.

Index the knowledge base and train the classifier (first run of the harness also does this):

```bash
python -m src.bootstrap
```

## Run the API

```bash
python -m src.api
```

- Demo UI: http://127.0.0.1:43123/
- Health: http://127.0.0.1:43123/health
- Submit a ticket: `POST /tickets`
- Engineered guardrail ticket: `POST /demo/guardrail`
- Prometheus: http://127.0.0.1:43123/metrics and port 8001
- Kill switch (no redeploy): `POST /ops/kill-switch` with `{"enabled": true}`

## Unattended evaluation (the gate)

The harness **must** take an input path and an output path. After submission it will be pointed at a hidden file of 120 tickets that is not in this repository (`Dataset_Guide.docx`, Build Specification A9).

```bash
python -m evaluation.harness --input data/validation_tickets.json --output evaluation/results
```

Outputs:

- `evaluation/results/results.jsonl` — one JSON object per ticket
- `evaluation/results/metrics.json` — volume, business, technical, governance
- `evaluation/results/summary.txt` — short human-readable recap

Every ticket produces `auto_respond`, `escalate`, or `block`. None are dropped.

## Tests

```bash
python -m pytest tests/ -v
```

CI runs the same command (`.github/workflows/ci.yml`). Tests set `RETRIEVAL_BACKEND=lexical` so they do not download a neural model.

## Repository layout

Matches `03_Reference/Setup_Guide.docx` §08:

```
README.md
requirements.txt
.env.example
src/            ingest, classify, retrieve, route, generate, guardrails, logging, api
prompts/        versioned prompt library
tests/
evaluation/harness.py
docs/           architecture and governance
data/           pack datasets (needed for a clean run)
workbooks/      completed stage artefacts
monitoring/     Prometheus scrape config
.github/workflows/ci.yml
```

`storage/` is created at runtime and is gitignored.

## Decision log

SQLite schema follows the Setup Guide. Count of distinct `ticket_id` values in `decisions` must match tickets processed (A8).

## What is not in this repository

- API keys
- The hidden 120-ticket assessment file
- A recorded video (you must appear on camera; see `workbooks/` for a shot list)
- Grafana running as a service — config is provided; the API metrics endpoint is enough to scrape

## Pack documents

Original assignment files are preserved under `capstone_pack/Capstone_Pack/`. Read those before changing behaviour.

## Honest limits

- CSAT is a proxy: there are no live customers.
- The printed pack deadline was 13 September; this implementation was completed after that printed date.
- Pack `requirements.txt` pins (`langchain==0.1.0`, `chromadb==0.3.21`) do not install on Python 3.12; this repo uses the same libraries at installable versions.
- Neural embeddings are optional. Default retrieval is lexical over the official 29-article corpus.
- Repeat-contact reduction cannot be measured from a single-run JSON file; the report states that gap.

## Attribution

Application code was written for this capstone with AI assistance (Cursor). The ticket data, documentation corpus, ground-truth answers, and stakeholder transcripts come from the course pack. LangChain, LangGraph, Chroma, scikit-learn, FastAPI, and Prometheus are third-party libraries.
