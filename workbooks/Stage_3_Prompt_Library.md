# Stage 3 — Prompt library (completed)

See also `prompts/README.md` (the runtime register). Files live in `prompts/system/` so they are not ignored by a Python `build/` directory rule.

## Requirement → specification

| Req | Spec | Inputs | Outputs | Acceptance |
|-----|------|--------|---------|------------|
| FR-01 | Normalise four channels; never throw | raw JSON | ticket dict | tests/test_ingest.py |
| FR-02/03 | Calibrated sklearn classifier; LLM prompt optional | ticket text | intent, urgency, confidence, alternatives | A3 |
| FR-04 | Chunk 800/120; return [] if below score | query | passages with doc_id | A4 |
| FR-05 | Threshold + always-escalate set + retrieval required | classification + hits | action + reason | A5 |
| FR-06 | Extractive or OpenRouter JSON; citations ⊆ retrieved | ticket + hits | message, citations, unknown | A6 |
| FR-07 | Five blocking checks | draft | pass/block | A7 |
| FR-09 | CLI paths | --input --output | metrics.json | A9 |

## Register

Copied from prompts/README.md. Build prompts delimit customer text. PR-BUILD-03 v1.1 used at runtime when an LLM key exists.

Checklist (Stage 3 Table 9): role vs task split — yes; inputs delimited — yes; output JSON specified — yes; unknown behaviour — yes; examples not only easy cases — classifier trained on 22 imbalanced classes; forbidden behaviour — yes (refunds, injection).

Traceability: every FR has a test id or harness metric. Gap: human dual-annotation of 50 drafts (PR-EVAL-01) not executed in this environment.
