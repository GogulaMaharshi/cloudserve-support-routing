# Stage 2 — PRD v1.1

Document control: Version 1.1 (revised after the first full validation run). Author: Maharshi Gogula. Status: implemented.

Problem statement: copied from Stage 1 §6 one-paragraph version.

## Users

| Group | Need | Today | Done when |
|-------|------|-------|-----------|
| Customers | Fast, honest first reply with a page they can check | Wait 8–12h; sometimes self-search | Reply in minutes or an explicit handoff |
| T1 agents | Draft + article, not another queue of wrong bot mail | Personal snippet files | Escalations include draft and doc_id |
| T2 | Uncertainty and what was tried | Raw forward | Packet with reason |
| Head of support | FCR, explainability, no public wrong answers | Red SLA | Decision log + metrics |

## Functional requirements

| ID | Requirement | Pri | Evidence | Acceptance |
|----|-------------|-----|----------|------------|
| FR-01 | Ingest email, chat, docs_comment, forum into one record preserving channel and original text | Must | Brief four channels; empty chat subjects | A2; tests/test_ingest.py |
| FR-02 | Classify intent among the 22 observed classes | Must | 22 intents in JSON | A3; per-class report |
| FR-03 | Classify urgency high/medium/low with confidence in [0,1] and alternatives | Must | Brief classify component | A3 |
| FR-04 | Retrieve ranked passages from documentation.json with real doc_id | Must | Ines; 29 docs | A4 |
| FR-05 | Route auto vs escalate with a measured threshold; deterministic; log reason | Must | Brief §05; Marcus wrong-answer fear | A5, A8 |
| FR-06 | Generate a cited draft or state unknown; ticket text cannot instruct the model | Must | Ravi honesty; injection note | A6 |
| FR-07 | Guardrails can block (PII, grounding, injection, commitments) | Must | Governance Table 5; Sofia follow-up fear | A7 |
| FR-08 | Persist decisions with Setup Guide fields | Must | Marcus compliance | A8 |
| FR-09 | Unattended harness `--input` `--output` over any schema-compatible file | Must | A9; hidden 120 | A9, A10 |
| FR-10 | Degrade on provider failure / empty retrieval / malformed input | Must | A11 | A11 |
| FR-11 | Kill switch without deploy | Should | Governance kill switch | POST /ops/kill-switch |
| FR-12 | Disclose automated replies | Should | Ravi | Generator text |
| FR-13 | Never auto-respond security, compliance, feature_request, unclear | Must | Daniel; must_not_auto labels | zero unsafe auto in metrics |

## Non-functional

| ID | Category | Requirement | Verify |
|----|----------|-------------|--------|
| NFR-01 | Latency | p95 < 3s end to end | harness |
| NFR-02 | Availability | Continue when LLM is missing | run without key |
| NFR-03 | Accuracy | Intent precision ≥85%; hallucination treated as block | harness + guardrail |
| NFR-04 | Privacy | Zero PII in sent text | pii guardrail |
| NFR-05 | Auditability | log count ≥ tickets | harness governance block |
| NFR-06 | Fairness | Report gaps; target <5 pts — **not met on all segments** | metrics.json fairness |
| NFR-07 | Cost | Free tier / local default | no key required |
| NFR-08 | Tests | one command | pytest |

## Out of scope

| Not building | Why | Reconsider if |
|--------------|-----|---------------|
| A conversational chatbot UI as the product | Brief Table 2 | Never as the graded deliverable |
| Training on agent snippet files | Daniel | After Ines reviews them into the KB |
| Refund / contractual language | Daniel; guardrail | Human billing queue |
| Live CSAT collection | No customers | Pilot |
| Paid model capacity | Instructions: no spend | Never for marks |
| The hidden 120-file in git | Not distributed | After official run |

## Assumptions

| Assumption | Why | If false | How we know |
|------------|-----|----------|-------------|
| Hidden set shares schema | Dataset Guide | Harness fails A9 | Path arguments |
| 71% answerable holds out of sample | Dev count | FCR target missed | Hidden run |
| Linear classifier generalises | Dev+val perfect on this pack | Precision <85% | Hidden run |
| Lexical retrieval is acceptable default | A11 + install reality | Retrieval hit collapses | Compare chroma extra |

## Success measures (official measurement tables, not the 65%/4.2 situation row)

| Measure | Baseline | Target | How | Reported by |
|---------|----------|--------|-----|-------------|
| FCR | 42% | ≥60% | auto_respond / n | harness |
| Reply time | 8–12h | <5 min | latency | harness |
| CSAT | 3.2 | ≥4.0 | proxy only | report |
| Escalation | 58% | ≤30% | escalate+block / n | harness |
| Repeat contacts | 21.6% | halved | **cannot** from one JSON run | stated as gap |
