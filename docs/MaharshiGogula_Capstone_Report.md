# CloudServe Support Routing System

**Capstone report**  
Maharshi Gogula  
Forward Deployed AI Engineering  
20 September 2026

---

## 1. Executive summary

CloudServe Solutions asked for a chatbot. The evidence in the course pack — five stakeholder transcripts and 500 labelled development tickets — does not support building one. Seventy-one percent of the development queue is already marked answerable from twenty-nine reviewed knowledge-base articles, while first-contact resolution in the same file is only 43.8 percent and historical escalation is 56.2 percent. The failure is delivery and abstention, not a missing conversational agent.

This project implements a six-stage routing pipeline: ingest four channels, classify intent and urgency with calibrated confidence, retrieve identifiable passages from `documentation.json`, route with a measured threshold, draft a cited reply, and **block** ungounded or unsafe text. A single command processes an arbitrary ticket file:

`python -m evaluation.harness --input <path> --output <path>`

On the 80-ticket validation file (a reusable check set per the Dataset Guide; **not** the hidden 120-ticket assessment file), a 2026-09-20 unattended run processed every ticket in 0.99 seconds, auto-responded 61, escalated 19, blocked 0, with weighted intent precision 1.0 on this pack, retrieval hit rate 0.89, FCR proxy 76.25 percent (target 60), escalation 23.75 percent (target ≤30), latency p95 0.014 seconds, complete decision-log coverage, and zero auto-responses on `must_not_auto_respond` tickets.

**Caveat:** those figures are validation, not hidden-set results. Intent scores on this synthetic pack are not a promise about unseen tickets. Customer satisfaction was not collected from live users. Repeat-contact reduction cannot be measured from a one-shot JSON file. Neural embeddings were not the default in this environment. A submission video with the student on camera is not included in this repository.

---

## 2. The problem

CloudServe is described in `01_Project_Brief.docx` as a ~150-person vendor with ~200 corporate customers and a support function that has outgrown informal process. The head of support, Marcus Adeyemi, reports more than 500 tickets a week, six agents, an eight-to-twelve-hour first reply against a two-hour agreement, 42 percent first-contact resolution, and CSAT 3.2/5. He asked for a chatbot because that is the mechanism he can picture.

`00_PROJECT_INSTRUCTIONS.docx` is explicit: if you build a chatbot you have answered the request and failed the project. A chatbot does not decide where an answer comes from, whether it is true, what happens when it is not known, or who is accountable.

Discovery (Stage 1) reframes the job as:

- put existing article text in front of the customer in minutes when retrieval is actually relevant;
- refuse to speak when it is not;
- hand specialists a packet (intent, passages, uncertainty) instead of a forwarded blob.

That is an operations-design problem with a language-model-shaped component, not a chat UX problem.

---

## 3. Discovery findings

Primary evidence is `Stakeholder_Interviews.docx` (CloudServe is fictional; these transcripts stand in for interviews) and counts from `development_tickets.json`.

**Finding 1 — Answers already exist.** Sofia Restrepo estimates seven in ten tickets are repeats. The file agrees: 357/500 tickets have `answerable_from_docs=true`. Ines Varga maintains 29 articles that she believes are accurate within the review cycle; every article in `documentation.json` has `last_reviewed_days_ago` of 0. The unstated brief hint (“a large share of volume is already answered in documentation”) is visible in the data.

**Finding 2 — Findability, not authoring, is the bottleneck.** Sofia does not search the official KB; she searches a personal file. Ines’s titles do not match customer phrasing. Daniel sees tier-two work that is “a link and two sentences.” The product implication is retrieval plus a draft, not more articles as the first intervention.

**Finding 3 — Escalation is under-instrumented.** Marcus watches the rate (about 58 percent). Daniel watches the contents (many should not have left tier one, and they arrive without a summary). History in the development file shows 56.2 percent escalated. The design treats a high-quality escalation as a feature (Brief Table 8).

**Finding 4 — Some classes must never auto-respond.** Daniel names security, billing commitments, and data location. The labels are sharper: `must_not_auto_respond` is true only for `security_incident`, `compliance_request`, `feature_request`, and `unclear_request` (87 tickets, all expected to escalate). Feature requests have no article (Ines). That set is hard-coded as always-escalate.

**Finding 5 — Honesty is a customer requirement.** Ravi Menon will act on a human answer without checking and will verify a machine answer. Hiding automation would itself be a failure. He also flags a business-versus-enterprise gap as a renewal issue; Marcus independently worries that enterprise customers will notice worse service.

**Finding 6 — Non-fluent tickets are a fairness hypothesis, not a slogan.** Sofia claims they have the worst CSAT. Development history barely shows it (non-fluent CSAT 3.04 vs fluent 2.95). Validation *history* does (1.95 vs 2.80). The workbook records the disagreement instead of picking the convenient table.

Figures that surprised: mean CSAT in the development history is 2.97, not 3.2; chat tickets have empty subjects (155/500); Latin America is only 60/500 tickets, so fairness slices will be noisy.

---

## 4. Requirements

Stage 2 identifiers FR-01–FR-13 and NFR-01–NFR-08 are listed in `workbooks/Stage_2_PRD.md`. Each FR cites a discovery row. Traceability into code:

| Req | Code |
|-----|------|
| FR-01 | `src/ingest.py` |
| FR-02, FR-03 | `src/classify.py` |
| FR-04 | `src/retrieve.py` |
| FR-05 | `src/route.py` |
| FR-06 | `src/generate.py`, `prompts/system/PR-BUILD-03_generate.txt` |
| FR-07 | `src/guardrails.py` |
| FR-08 | `src/logging_store.py` |
| FR-09, FR-10 | `evaluation/harness.py`, `src/pipeline.py` |
| FR-11 | `POST /ops/kill-switch` |
| FR-13 | `ALWAYS_ESCALATE_INTENTS` in `src/config.py` |

Targets used for success measures are the **measurement** tables (FCR ≥60%, CSAT ≥4.0 proxy, escalation ≤30%, p95 <3s), not the situation-table 65% / 4.2, which contradict them inside the same brief. Reply-time SLA remains two hours; the system target is under five minutes.

---

## 5. Architecture and design

See `docs/architecture.md`. Alternatives considered:

1. **Chatbot over the KB.** Rejected: Brief §02 and Instructions Table 2.
2. **LLM classifier for 22 intents.** Rejected as default: A5 determinism, cost, and the existence of development labels. Kept as a prompt (`PR-BUILD-01`) for a later swap.
3. **Always call OpenRouter to write answers.** Rejected as default: no key in this environment; A11; free-tier throttling. Extractive grounding is the default; OpenRouter is used when configured.
4. **Chroma + MiniLM only.** Specified in Brief Table 15. Retained as an extra (`requirements-embeddings.txt`). Default is TF-IDF over the same chunks so CI and air-gapped runs still retrieve real `doc_id`s.
5. **Threshold 0.80.** Illustrative in the brief. Binding constraint on the first val pass was retrieval score, not confidence (almost all tickets were in the 0.8–1.0 confidence band). Threshold 0.72 plus “must retrieve something.”

LangGraph encodes the six Brief components as nodes. FastAPI exposes `/tickets`, a small demo page at `/`, and Prometheus metrics. That demo page is a window onto the router, not the product metaphor.

---

## 6. Implementation

The Setup Guide layout is followed (`src/*.py`, `prompts/`, `tests/`, `evaluation/harness.py`, `.github/workflows/ci.yml`). Packaged pins from `06_Configuration/requirements.txt` were not installable on Python 3.12 (`langchain==0.1.0`, `numpy==1.24.0`, `chromadb==0.3.21`). The repo pins the **same libraries** at versions that install. That deviation is in the revision log.

Difficulties: (1) pin resolution; (2) first retrieval floor of 0.28 with TF-IDF yielded only 35% FCR because too many queries returned nothing; dropping the floor to 0.12 and prepending titles raised retrieval hit rate from 0.47 to 0.89; (3) a blanket FastAPI exception handler must not hide missing tickets in the log — coverage is reconciled in the harness.

What I would restructure: split “pipeline summary” log rows from per-stage rows so A8 reconciliation is one row per ticket by default (today distinct ticket_id still matches).

---

## 7. Evaluation

**Method.** `python -m evaluation.harness --input data/validation_tickets.json --output evaluation/results` on 2026-09-20. One process, no manual retries. Backend `RETRIEVAL_BACKEND=lexical`. No OpenRouter key. Classifier trained on the 500 development tickets only.

**Hidden set.** Not in the pack. **Times run against hidden 120: 0.** The report cannot honestly fill that cell. The harness is path-parameterised so an assessor can point it at that file.

**Validation file use.** Dataset Guide allows repeated use of the 80 tickets. Project Brief Table 9 contradicts that. This work follows the Dataset Guide and README, and still treats the hidden file as the grade-bearing set.

**Results (n=80).** See `evaluation/results/metrics.json`.

| Measure | Baseline | Target | Achieved (validation) | Confidence in figure |
|---------|----------|--------|------------------------|----------------------|
| FCR proxy (auto_respond) | 42% | ≥60% | 76.25% | Medium — not hidden set; conservative on safety classes |
| Escalation | 58% | ≤30% | 23.75% | Medium |
| Intent precision (weighted) | — | ≥85% | 100% | Low–medium — synthetic separability |
| Retrieval hit (expected doc_id ∩ retrieved) | — | — | 88.7% | Medium |
| Routing agreement with labels | — | — | 73.8% | Medium |
| Latency p95 | — | <3s | 0.014s | High on this path |
| Unsafe auto-respond | — | 0 | 0 | High |
| Decision log coverage | — | 100% | true | High |
| PII sent | — | 0 | 0 blocks on val (demo ticket blocks) | Medium |
| CSAT | 3.2 | ≥4.0 | not measured live | — |
| Repeat contacts | 21.6% | halved | not measurable here | — |

Fairness auto-respond rates (validation): enterprise 87.5% (n=8), business 83.3% (n=30), standard 69.0% (n=42), fluent 75.4%, non-fluent 79.0%, Latin America 57.1% (n=7). Variation from the best segment exceeds five points for standard vs enterprise and for Latin America. **NFR-06 as a deploy condition is not met.** It is reported.

Calibration: stated confidence in the 0.8–1.0 band averaged 0.85 with observed intent accuracy 1.0 on this file (gap −0.15). The model is underconfident relative to this pack, which is safer for routing than the reverse.

**The figures above should be treated with caution because** they come from a labelled synthetic validation file that the engineer could inspect, the classifier saw related development tickets, no dual-annotator hallucination study of fifty drafts was performed, CSAT is not a customer rating, and the hidden 120 has never been run.

Business interpretation: if validation-like tickets arrived in production on this configuration, first-line volume answered without a human would exceed Marcus’s 60 percent measurement target while keeping the four unsafe classes on the human path. That would not by itself move live CSAT.

---

## 8. Governance and risk

`docs/governance.md` holds the register, incident steps, and kill switch. Guardrails match Governance Table 5. Decision logging matches the Setup Guide SQL plus a payload column.

Most likely real harm after controls: a cited but wrong article sent to a customer who trusts the citation (Ravi will still verify if he knows it is automated; disclosure is in the extractive template). Secondary: fairness gaps on small regional slices.

---

## 9. Requirements revision

Stage 5 records the compulsory change: installable dependencies, lexical retrieval as a first-class backend, fairness as a measured miss rather than a hoped-for pass, threshold not copied from the 0.80 figure, and FR-13 from measured `must_not_auto_respond` classes. Trigger: the first unattended run and the failed pack pins, not wording tidy-up.

---

## 10. Conclusions

Next: run the hidden file once when provided; sample fifty drafts with two readers; enable MiniLM in environments that can store the model; shadow-mode for enterprise customers (Marcus, Ravi).

Still uncertain: whether 100 percent intent accuracy is a pack artefact; whether Latin America’s 57 percent auto-rate is noise (n=7); whether live engineers will accept extractive tone.

The client asked for a chatbot. The system that should be shown to them is a router that knows the 29 articles, knows when it does not, and can be turned off without a deployment.

---

## Appendix notes

Completed workbooks: `workbooks/`. Prompt register: `prompts/README.md`. Full metrics: `evaluation/results/metrics.json`. Architecture: `docs/architecture.md`.

### Declaration of AI tool use

Cursor (Grok) was used to draft and debug application code, convert pack `.docx` files to text for inventory, and help assemble this report. Discovery counts and interview quotes were taken from the pack files, not invented by the model. Thresholds, the always-escalate set, and the decision to default to lexical retrieval were chosen by the author after looking at measured outputs. Undeclared use would be dishonest; this paragraph is the required declaration (`00_PROJECT_INSTRUCTIONS.docx` §09).
