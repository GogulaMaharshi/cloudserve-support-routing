# Stage 1 — Discovery workbook (completed)

Evidence sources: `capstone_pack/.../Stakeholder_Interviews.docx` and `data/development_tickets.json` (500 tickets). Figures below were counted from the JSON, not taken on trust from Dataset_Guide Table 9.

## 1. Interviews

| Who | What they told you | What they appear not to know | Verify in data |
|-----|--------------------|------------------------------|----------------|
| Marcus Adeyemi, Head of Support | Volume >500/week, 6 agents, first reply 8–12h vs 2h SLA. FCR 42% is the number he actually cares about; response time is what is reported. Failure = wrong answer in public or more agent work. Enterprise agreements differ. Needs explainability for an autumn compliance review. | Intent breakdown (“I would be guessing”). What is inside escalations. | Channel/intent mix; FCR; escalation contents |
| Sofia Restrepo, T1 | Queue 40–70/morning. ~7/10 repeats. Time goes to **finding** answers, not knowing them. Docs exist but search is painful; agents keep private snippet files. Escalates when unsure or on security. Non-fluent tickets take longer and have worse CSAT. Wants draft + page, not a naked bot. | That Marcus does not see findability as the core metric. | Repeat intents; fluency vs CSAT |
| Daniel Okonkwo, T2 | ~Half of his queue could have been closed at T1 with confidence or the right page. Escalations arrive as raw forwards. Do not train on private snippet files (stale). Never auto security, billing commitments, data location. | Marcus’s view of escalation quality. | Escalation rate vs “could have been auto” |
| Ines Varga, writer | 29 KB articles, reviewed, unused internally because keyword search misses customer phrasing (“deployment keeps dying” vs “container health check”). Wants citations so she can tell article-wrong vs retrieval-wrong. No docs for feature requests, roadmap, novel incidents. | How often T1 reconstructs her articles from memory (she noticed yearly). | 29 articles; answerable_from_docs rate |
| Ravi Menon, customer | Slow but decent. Waiting cost depends on urgency (failed deploy vs pagination). Finds answers himself ~half the time, then gets the same reply. Accepts automation if honest and cited; must know it is a machine. Business vs enterprise gap is a renewal issue. | Internal search failure; private snippet files. | Urgency vs channel; tier outcomes |

### Disagreements (settled with data)

| Disagreement | Who | Data | Follows |
|--------------|-----|------|---------|
| What share of work is “easy repeats”? | Sofia ~70%; Marcus does not know | 357/500 (71.4%) `answerable_from_docs=true`; 22 intents with a long tail of repeats | Build retrieval, not a general chatbot |
| Are escalations mostly hard? | Daniel says ~half are T1-completable; Marcus reports 58% escalate as if they were hard | 189/500 (37.8%) labelled `expected_route=escalate`; 87/500 must never auto | Escalation packet with draft+sources is the T2 feature |
| Is documentation the problem? | Sofia: docs fine, search bad. Ines: titles vs customer language | Corpus exists (29). History FCR 43.8% despite 71% answerable | Findability + routing, not more articles as the first move |
| Non-fluent quality | Sofia: worst CSAT. Dev set: non-fluent CSAT 3.04 vs fluent 2.95 (tiny gap). Val history: non-fluent CSAT 1.95 vs fluent 2.80 | Split: **do not** treat the development history as proof Sofia is wrong; validation history supports her | Fairness audit on both sets |

### Never mentioned

| Missing | Why expected | How checked |
|---------|--------------|-------------|
| Chat vs email behaviour | Brief lists four channels | Dev: email 212, chat 155, docs_comment 78, forum 55. Chat subjects empty. |
| Citation / audit trail (except Marcus compliance) | Governance | Only Marcus and Ines approach it |
| Private snippet files as a **training** risk | Daniel only | System retrieves only `documentation.json` |

## 2. Ticket counts (development_tickets.json)

| Measure | Figure | Source | Surprise |
|---------|--------|--------|----------|
| N | 500 | JSON length | — |
| Channel | email 212, chat 155, docs_comment 78, forum 55 | `channel` | Email still largest, as the guide said |
| Intents | 22 classes, top: data_export 29, data_residency 29, rollback 28, deployment_failure 27 | `labels.intent` | No single “password” monopoly; residency/compliance are large |
| Urgency | medium 226, high 146, low 128 | labels | — |
| History FCR | 43.8% | history.first_contact_resolution | Matches Marcus 42% |
| History CSAT | mean 2.97 / 5 | history.csat_rating | Brief says 3.2; **sample is slightly worse** |
| History escalated | 56.2% | history.escalated | Matches ~58% |
| Answerable from docs | 71.4% | labels.answerable_from_docs | The unstated finding the Brief told us to find |
| Expected auto | 62.2% | labels.expected_route | — |
| Non-fluent | 120/500 = 24% | language_fluency | Guide said ~quarter |
| Repeat contact | 21.6% | history.repeat_contact | Baseline for “halve repeats” |
| Mean resolution minutes | 422 | history | ~7 hours, inside 8–12h story |
| Empty subject | 155 | all chat | Ingest must allow empty subject |
| must_not_auto | 87, all escalate; intents security, compliance, feature_request, unclear | labels | Hard safety set |

## 3. Effort vs volume

| Category | Volume share | Effort hypothesis | Why they differ | Evidence |
|----------|--------------|-------------------|-----------------|----------|
| Answerable repeats | 71% | Low minutes if findable; high today because of search | Sofia 4–5 min vs 40 min | Interview 2; answerable flag |
| Security/compliance | ~10% combined | High / always escalate | Policy | must_not_auto |
| Feature + unclear | ~7% | Zero auto value | No article (Ines) | labels |
| Non-fluent | 24% | Extra clarification loops | Sofia; val history CSAT | fluency × history |

Sofia’s steps: open oldest → interpret (longer if non-fluent) → search docs or personal file → write → send or escalate. Automate search + first draft; do not automate security/billing commitments.

## 4. What the client counts as success

| Measure | Who | Current | Success | Confidence |
|---------|-----|---------|---------|------------|
| First contact resolution | Marcus (actually cares) | 42% (brief) / 43.8% (dev history) | 60% measurement table; 65% his benchmark | High |
| Time to first reply | Exec via SLA | 8–12h | Contract 2h; system target <5 min (Brief Table 11) | High |
| CSAT | Exec / renewals | 3.2 brief / 2.97 sample | 4.0 measurement table; 4.2 situation table | Medium (proxy only) |
| Escalation rate | Marcus/Daniel | 58% | ≤30% | High |
| Wrong public answer | Marcus | n/a | Zero tolerance | High |
| Enterprise fairness | Marcus, Ravi | Ravi sees ~1h enterprise | Do not widen the gap | Medium |

Sentence test: This project is worth doing if, within three months, first-contact resolution is at least 60% and first reply is minutes rather than hours **without** sending ungrounded answers to engineers who will screenshot them. We will know it failed if T1 spends time apologising for machine errors (Sofia) or if business-plan customers see a worse gap at renewal (Ravi). The number Marcus is judged on internally is FCR, even though the SLA number is response time.

## 5. Data and risk

| Source | Contains | Quality | Constraints | PII |
|--------|----------|---------|-------------|-----|
| Support tickets | 500 + 80 labelled | Synthetic but schema-stable | Hidden 120 not here; harness must take a path | Names in tickets; do not echo other customers |
| Documentation | 29 articles | Ines: reviewed (`last_reviewed_days_ago` = 0 for all 29) | Only this corpus | None expected |
| Ground truth | 200 DEV answers | Senior agent | Not the test set | — |
| Customer records | ids, tier, region | No extra CRM | Do not load external PII | names |

Initial risks: wrong confident answers; PII leak; injection; fairness; stale private snippets if we trained on them (we do not).

## 6. Problem statement

**Asked for:** a chatbot (`00_PROJECT_INSTRUCTIONS.docx` Table 2; Marcus interview).

**Actually needed:** a way to deliver answers that already exist in 29 reviewed articles (71% of the development queue) within minutes, and to pass the rest to humans **with** the suspected intent, the passages, and the uncertainty — without auto-responding on security/compliance/feature/unclear tickets.

**Gap:** the named mechanism (chat) does not include retrieval, abstention, citations, or escalation packets.

**Who:** customers waiting (Ravi), T1 searching (Sofia), T2 re-reading threads (Daniel), Marcus reporting red SLA/FCR, Ines owning unused articles.

**If solved:** FCR and reply time move; T2 sees fewer “paste a link” tickets; compliance review can reconstruct decisions.

**Out of scope:** replacing product docs, staffing, outsourcing, training on private snippet files, contractual refunds, roadmap promises.

### One paragraph (no ML vocabulary)

CloudServe’s support team is missing its two-hour reply promise and resolving only about two tickets in five on first contact, not because nobody knows the answers, but because the answers sit in a knowledge base that agents and customers cannot reliably find, while the remaining tickets — especially security, compliance, and anything unclear — are forwarded to specialists with no summary of what was already tried. The organisation asked for a chatbot. What would change the numbers is a first-line system that returns the matching article in minutes when the match is real, says so when it is guessing, and otherwise hands an engineer a draft plus the page it came from.

Checked against all five transcripts: Marcus gets FCR and “don’t be wrong”; Sofia gets search and drafts; Daniel gets context-rich escalations and no snippet-training; Ines gets citations; Ravi gets honesty and disclosure.
