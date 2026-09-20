# Prompt register

Prompts are design artefacts. Version numbers change when the text changes.

| ID | File | Category | Serves | Version | Notes |
|----|------|----------|--------|---------|-------|
| PR-BUILD-01 | system/PR-BUILD-01_classify.txt | Build | FR-02, FR-03 | 1.0 | Used when an LLM classifier is enabled. Default runtime uses the calibrated sklearn model. |
| PR-BUILD-02 | system/PR-BUILD-02_retrieve.txt | Build | FR-04 | 1.0 | Query rewrite; optional. Default uses the normalised ticket text. |
| PR-BUILD-03 | system/PR-BUILD-03_generate.txt | Build | FR-06 | 1.1 | Ticket text delimited. Unknown is preferred to invention. |
| PR-EVAL-01 | evaluation/PR-EVAL-01_grounding.txt | Evaluation | NFR-03 | 1.0 | Human/LLM judge for hallucination sampling. |
| PR-EVAL-02 | evaluation/PR-EVAL-02_quality.txt | Evaluation | NFR-03 | 1.0 | CSAT proxy rubric. |
| PR-REV-01 | review/PR-REV-01_spec_review.txt | Review | Stage 3 | 1.0 | Spec quality, not runtime. |

Injection defence: every build prompt states that ticket text is data inside `<<<CUSTOMER_TICKET>>>` markers. Guardrail `instruction_integrity` blocks known injection phrases before send.
