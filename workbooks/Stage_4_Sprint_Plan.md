# Stage 4 — Sprint plan

Capacity: this implementation was produced in a single compressed build after the pack was inventoried. Planned “three weeks” from the pack are mapped to logical stages, not calendar weeks after 13 September.

## Backlog

| ID | Item | Hours (actual order) | Pri | Depends | Done means |
|----|------|----------------------|-----|---------|------------|
| B-01 | Env, gitignore, env example | done | Must | — | pip install works |
| B-02 | Ingest | done | Must | B-01 | four channels tests |
| B-03/04 | Chunk + retrieve | done | Must | B-02 | doc_id hits |
| B-05 | Harness | done | Must | B-02 | --input --output |
| B-06 | Classifier | done | Must | B-02 | confidence + alternatives |
| B-07 | Routing | done | Must | B-06 | deterministic |
| B-08 | Generate + citations | done | Must | B-04 | extractive + optional LLM |
| B-09 | Guardrails | done | Must | B-08 | POST /demo/guardrail blocks |
| B-10 | Decision log | done | Must | B-07 | sqlite coverage |
| B-11 | Unattended val run | done | Must | B-05,B-09 | metrics.json |
| B-12 | Prometheus | done | Should | B-10 | /metrics |
| B-13 | GitHub Actions | done | Must | tests | ci.yml |
| B-14 | Fairness table | done | Must | B-11 | metrics fairness |
| B-15 | Report + workbooks | done | Must | all | this folder |
| — | Student video | not done | Must for zip | B-15 | Maharshi on camera |

## Drop order if time ran out

1. Grafana docker — keep /metrics  
2. Neural embeddings extra — keep lexical  
3. LLM generation — keep extractive  

Never drop: harness paths, guardrail block, decision log, four-channel ingest.
