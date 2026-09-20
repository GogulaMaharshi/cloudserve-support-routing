# Governance

Filled against `03_Reference/Governance_Framework.docx`. This is the design, not a late appendix.

## Position (declaration)

| Statement | Position |
|-----------|----------|
| This system must never … | send a customer an ungrounded or identity-bearing answer, make a refund or delivery commitment, or auto-respond to security, compliance, feature-request, or unclear tickets |
| The mechanism that enforces that is … | always-escalate intent set + retrieval floor + blocking guardrails + kill switch |
| The most likely remaining harm is … | a fluent, cited answer that is still the wrong article for a non-fluent writer (Ines + Sofia; fairness table) |
| We would not deploy without first … | a hidden-set run, a 50-draft dual review, and enterprise-customer shadow mode |

## Decision logging

Every ticket writes classification, retrieval, routing, generation, validation, and a pipeline summary. Schema: `src/logging_store.py`. Coverage is checked in the harness (`distinct_tickets_logged >= tickets_processed`).

Minimum JSON shape from Governance Table 1 is stored across columns + `payload`.

## Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|----|------|------------|--------|------------|-------|
| R-01 | Confident wrong answer | Medium | High | Retrieval floor, grounding block, prefer escalate | Maharshi Gogula |
| R-02 | Private data in outbound text | Low | High | PII regex block; never redact-and-send | Maharshi Gogula |
| R-03 | Ticket treated as instruction | Medium | High | Delimiters + injection guardrail | Maharshi Gogula |
| R-04 | Worse answers for some groups | High | Medium | Fairness split in harness; report gaps | Maharshi Gogula |
| R-05 | Stale documentation | Medium | High | Corpus is the 29 reviewed articles only; no private snippet files (Daniel) | Maharshi Gogula |
| R-06 | Model provider down | High on free tier | Medium | Extractive fallback; escalate if ungrounded | Maharshi Gogula |
| R-07 | Latency under load | Low at this volume | Medium | No sequential LLM on default path | Maharshi Gogula |
| R-08 | Cost blow-up | Low | Low | Default path is local sklearn + lexical/chroma | Maharshi Gogula |

## Guardrails

See `src/guardrails.py`. Demo: `POST /demo/guardrail`.

## Kill switch

| Question | Answer |
|----------|--------|
| Mechanism | `storage/KILL_SWITCH` file or `KILL_SWITCH=true` or `POST /ops/kill-switch` |
| Who | Support lead (Marcus's role) or on-call engineer |
| Time to effect | Next ticket; no deploy |
| In-flight tickets | Finish current ticket, then escalate |
| How tested | Unit route test + API endpoint |

## Incident procedure

| Step | What | Who | Time |
|------|------|-----|------|
| 1 Detect | Spike in guardrail blocks, customer complaint, or CSAT drop | On-call | 15 min |
| 2 Contain | Enable kill switch | On-call | 2 min |
| 3 Assess | Export decisions for affected ticket_ids | Engineer | 1 hour |
| 4 Notify | Head of support + affected customers if a wrong answer was sent | Head of support | same day |
| 5 Remediate | Fix prompt/threshold/docs; add a test | Engineer | 1–2 days |
| 6 Review | Write which requirement_id and prompt_version failed | Engineer + head of support | 1 week |

## Fairness (validation run 2026-09-20)

See `evaluation/results/metrics.json`. Auto-respond rate varied by more than five points across tiers and regions. Latin America was the weakest segment (n=7). That is reported, not smoothed. Non-fluent auto-rate was not worse than fluent on this run; historical CSAT on the validation **history** block still is (Dataset Stage 1).
