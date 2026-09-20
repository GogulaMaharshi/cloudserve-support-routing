# Stage 5 — PRD revision log (compulsory)

| Field | Value |
|-------|-------|
| New version | 1.1 |
| Date | 2026-09-20 |
| Who | Maharshi Gogula |
| Requirements changed | NFR-06 (report actual fairness gaps), FR-10 (lexical fallback as first-class), dependency note |
| Added | FR-13 always-escalate classes from measured labels |
| Removed | Implicit “use pack pins as-is” |

## Changes

| ID | v1 | now | Trigger |
|----|----|-----|---------|
| deps | Copy pack requirements.txt literally | Installable 3.12 pins of the same stack | langchain==0.1.0 / chromadb==0.3.21 do not resolve |
| retrieve | Chroma+MiniLM only | lexical default, chroma optional | Clean CI and A11 without torch download |
| NFR-06 | “will be <5 pts” | “measure and report; val run missed on region/tier” | fairness table after first full val run |
| threshold | 0.80 from the figure | 0.72 + retrieval floor | Brief says 0.80 is illustrative; retrieval was the binding constraint |
| FCR/CSAT targets | mixed 60/65 and 4.0/4.2 | measurement tables 60% and 4.0 | contradiction in Project Brief |

## Assumptions

| v1 assumption | Held? | Found | Change |
|---------------|-------|-------|--------|
| Pack pins install on 3.12 | No | Resolver failures | requirements.txt retargeted |
| Validation is look-once | Contradicted by Dataset Guide | Used as reusable check | Documented policy |
| MiniLM always available | No in this environment | No API key, no embeddings extra | lexical backend |
| Intent model needs LLM | No | 22-class linear separation on this pack | sklearn default |

## Not changed

| Looked wrong | Left | Cost to change | Revisit |
|--------------|------|----------------|---------|
| Perfect intent scores on val | Not inflated by hand | Would hide a real pack artefact | Hidden 120 |
| FCR 76% vs 60% target | Conservative safety still in always-escalate | Lowering threshold further risks R-01 | After hidden run |
| No video | Cannot appear as the student | — | Student records it |

## Reflection

v1 over-weighted the illustrated architecture (chat + MiniLM + 0.80) and under-weighted install and A11. Discovery already said “wrong answers are worse than silence”; the revision tightened abstention and made the fallback explicit. Starting again, the first code would still be ingest + harness paths, not the model provider.
