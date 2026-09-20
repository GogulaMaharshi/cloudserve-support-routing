# Effort log

Full name: Maharshi Gogula  
Project start (pack calendar): week of 24 August 2026 (documents)  
Implementation recorded: 20 September 2026  
Target printed in pack: 13 September 23:59  

This log is **not** reconstructed as three weeks of fictional 2-hour days. The pack was read in full, then the system was built and evaluated in one session. That compression is a limitation of how the work was done, not a claim that discovery took the textbook 8 hours.

## Hours by stage (this session)

| Stage | Hours (approx) | Notes |
|-------|----------------|-------|
| 1 Discovery (read transcripts + count JSON) | 1.5 | All five interviews; measured 500+80 |
| 2 PRD | 0.5 | Traceable FR list |
| 3 Prompts | 0.4 | files under prompts/ |
| 4 Sprint | 0.2 | B-01–B-15 |
| 5 Build, eval, revision | 4.0 | pipeline, tests, val harness, threshold/retrieval |
| 6 Report, workbooks, packaging | 1.5 | |
| Total | ~8 | Plus assignment-pack reading |

## Daily entries

| Date | Task | Stage | Hours | Produced | Blocked |
|------|------|-------|-------|----------|---------|
| 2026-09-20 | Inventory zip; extract requirements | 1 | 1.0 | inventory | contradictions listed |
| 2026-09-20 | Implement pipeline + tests | 5 | 3.0 | src/, tests/ | pack pins on 3.12 |
| 2026-09-20 | Validation harness run | 5 | 0.5 | evaluation/results | retrieval floor too high, then retuned |
| 2026-09-20 | Docs and workbooks | 6 | 1.5 | README, workbooks, report | video cannot be recorded here |

## Estimates vs reality

| Item | Estimated | Actual | Why |
|------|-----------|--------|-----|
| Pack pin install | 10 min | failed, rewrite requirements | Python 3.12 |
| Classifier | 2 h LLM | 20 min sklearn | labels exist |
| Retrieval | MiniLM default | lexical + optional chroma | environment |
| Full val run | “slow LLM” | ~1 s / 80 tickets | no LLM on path |
| Video | 0.5 day | not done | requires the student on camera |

Which took longer: making installable dependencies without abandoning the named stack.  
Which was easier: intent classification on this synthetic set.  
Allocate differently: harness + ingest first, provider last.  
Time that did not matter: treating 0.80 as a real threshold.
