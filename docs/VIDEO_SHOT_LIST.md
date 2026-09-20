# Video shot list (you must appear on camera)

The Submission Guide requires a ~20 minute MP4, you visible at open and close, and at least seven minutes of live demo.

Suggested order (`04_Submission/Submission_Guide.docx` Table 4):

1. 0–2 min — Client asked for a chatbot; evidence says findability + unsafe automation.
2. 2–5 min — Sofia (search), Daniel (empty escalations), Ines (titles vs customer language), ticket counts.
3. 5–7 min — Six-stage diagram from `docs/architecture.md`.
4. 7–14 min live:
   - Demo UI ticket that auto-responds with citations (e.g. DEV-0001 text).
   - Escalation: security or empty retrieval.
   - `POST /demo/guardrail` block.
   - Terminal: `python -m evaluation.harness --input data/validation_tickets.json --output evaluation/results` already finished; show `summary.txt` and the SQLite log.
5. 14–17 min — FCR, escalation, precision, fairness caveat, hidden set not run.
6. 17–18 min — Kill switch and R-01.
7. 18–20 min — PRD revision (dependency pins, retrieval backend) and next steps.

File name when you record: `MaharshiGogula_Capstone_Video.mp4`.
