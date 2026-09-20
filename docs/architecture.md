# Architecture

This note justifies the runtime design against `01_Read_First/01_Project_Brief.docx` and `01_Read_First/02_Build_Specification.docx`.

## What we are not building

A chatbot. The brief states that a chatbot is a delivery mechanism and does not decide where answers come from, when to stay silent, or who is accountable (`01_Project_Brief.docx` §02). The product is a **support routing system**: ingest four channels, retrieve from the 29-article knowledge base, answer only when grounded, escalate with context otherwise.

## Components

```
ticket JSON
    → ingest (one internal record)
    → classify (intent, urgency, calibrated confidence, alternatives)
    → retrieve (ranked passages with doc_id, or nothing)
    → route (auto_respond | escalate, reason in plain language)
    → generate (cited draft; unknown is allowed)
    → validate (blocking guardrails)
    → outcome + SQLite decision log + Prometheus metrics
```

Orchestration uses LangGraph (`src/pipeline.py`) so the six stages are explicit nodes rather than a hidden script.

## Classification

A TF-IDF + calibrated logistic regression trained on `data/development_tickets.json`. Chosen because:

- Routing must be **deterministic** (A5). A temperature-0 LLM still varies with provider noise.
- Confidence must mean something (Brief §05; Evaluation Framework calibration). `CalibratedClassifierCV` is a stated method, not a raw logit.
- Free-tier constraint: calling a model 500 times to label tickets during development is unnecessary when labels already exist on the development set.

The OpenRouter prompt `PR-BUILD-01` remains in the library if a later revision swaps the sklearn head for an LLM head.

Always-escalate intents were not guessed: they are the four classes where `must_not_auto_respond` is true in the development file (`security_incident`, `compliance_request`, `feature_request`, `unclear_request`).

## Retrieval

Corpus: `data/documentation.json`, 29 articles, field `doc_id` (the Setup Guide snippet uses `doc["id"]`; that field does not exist — Dataset Guide schema wins).

Chunking: RecursiveCharacterTextSplitter, 800/120, splitting on markdown headings first so resolution steps stay together (Dataset Guide §2 warning). Title is prepended to each chunk.

Two backends:

| Backend | When | Why it is still A4 |
|---------|------|--------------------|
| `chroma` + MiniLM | `pip install -r requirements-embeddings.txt` and `RETRIEVAL_BACKEND=chroma` | Project Brief Table 15 |
| `lexical` TF-IDF | default, CI, embedding download failure | Same corpus, same `doc_id` / `passage_id` |

Irrelevant hits are dropped below `RETRIEVAL_MIN_SCORE` (default 0.12). Returning nothing is a valid answer (Build Spec §08).

## Routing threshold

The 0.80 figure in the Brief is illustrative. Default `CONFIDENCE_THRESHOLD=0.72` plus a retrieval-must-exist rule. On the 80-ticket validation file (used as a reusable check set per Dataset Guide, **not** the hidden 120), this produced FCR 76.25% and escalation 23.75% with **zero** auto-responses on `must_not_auto_respond` tickets. Those figures will not be claimed as hidden-set results.

## Generation

If `OPENROUTER_API_KEY` is set: JSON draft via OpenRouter, citations filtered to retrieved `doc_id`s. On timeout, 401, or parse failure: extractive fallback (A11). Without a key: extractive only. Replies disclose that they are automated (Ravi Menon transcript).

Ticket text is wrapped in `<<<CUSTOMER_TICKET>>>` markers (Build Spec Generate; Prompt Library injection note).

## Guardrails

All run on every draft. Status `block` stops the send (A7). Types: `pii`, `grounding`, `instruction_integrity`, `tone_scope`, `confidence_floor`. Private data is blocked and escalated, not redacted-and-sent (Governance Table 5).

Kill switch: `KILL_SWITCH=true` or file `storage/KILL_SWITCH`, also `POST /ops/kill-switch`. Takes effect on the next ticket without a deploy.

## Persistence and monitoring

SQLite `decisions` table as in Setup Guide §05, plus a JSON `payload` column for alternatives. Prometheus counters/histograms as in Setup Guide §06. Grafana is optional Docker; the scrape target is the API.

## What we would change with more time

- Fit the threshold on a held-out slice of development tickets only, then freeze it before touching validation.
- Dual annotator hallucination sample of 50 drafts (Evaluation Framework). This checkout scores grounding automatically via citation membership, which is weaker than human judgement.
- Neural embeddings as default once the MiniLM cache is part of the environment image.
