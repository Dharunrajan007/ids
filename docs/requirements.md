# Requirements — Phase 0 (FROZEN v1.0, 2026-07-28)

> This document is frozen. It is not edited after this date; any change is recorded
> as a new ADR in [DECISIONS.md](DECISIONS.md) instead.

## Stakeholders

| Stakeholder | Interest | Needs |
|---|---|---|
| Developer/presenter (student) | Learn IDS + ML, pass review | Understandable code, explainable decisions |
| Professor / review panel | Assess depth and understanding | Working demo, clear architecture, honest evaluation |
| Future self (viva prep) | Fix/adjust weeks later | Documentation, consistent structure |

## Functional requirements

- **FR1** Load and preprocess the NSL-KDD dataset into model-ready form.
- **FR2** Train a classifier labelling a flow as **normal** or **attack** (binary).
- **FR3** Classify attacks into 4 categories: DoS, Probe, R2L, U2R (multi-class).
- **FR4** Report per-model evaluation: confusion matrix, precision, recall, F1 (per class + aggregate).
- **FR5** Expose predictions over HTTP: one flow's features in → prediction, attack type, confidence out.
- **FR6** Traffic simulator replays test-set flows to the API at a configurable rate.
- **FR7** Dashboard shows: live prediction feed, alert list, traffic-over-time chart, attack-type breakdown, counters.
- **FR8** Clicking an alert shows flow details and model confidence.

## Non-functional requirements

- **NFR1 Performance** — single prediction < 200 ms locally; training < 10 minutes.
- **NFR2 Resources** — runs fully on one Windows laptop, no internet during demo.
- **NFR3 Simplicity** — full system runs with ≤ 3 commands from the README.
- **NFR4 Explainability** — every column, metric, and decision has a written explanation.
- **NFR5 Consistency** — identical preprocessing at train and predict time (one serialized Pipeline).
- **NFR6 Robustness** — API rejects malformed input with clear errors, never crashes.

## Scope

**In:** offline training on NSL-KDD, binary + multi-class classification, evaluation
reports, prediction API, simulated live traffic, React dashboard, documentation.

**Out (explicitly):** live packet capture, blocking/prevention (IPS), deep learning,
authentication, databases, deployment beyond localhost, real-time guarantees,
CICIDS2017 (unless optional Milestone 9 is reached).

## Success criteria

1. Binary model substantially beats the majority-class baseline; per-class recall
   reported honestly on validation split **and** official KDDTest+.
2. Multi-class confusion matrix is sane (DoS/Probe strong; weak R2L/U2R acceptable and explained).
3. End-to-end demo: API + simulator + dashboard shows live classifications within 10 s of starting.
4. The presenter can answer unaided: "What is a flow?", "What does feature X mean?",
   "Why is accuracy misleading here?", "Why FastAPI/React/scikit-learn?"
5. A fresh clone runs from the README alone.

## User journey (demo flow)

```
Professor sits down
 → start API (terminal 1), simulator (terminal 2), dashboard (browser)
 → counters at zero, flows begin streaming
 → green rows = normal, red alert rows appear
 → charts update live (traffic line, attack-type donut)
 → professor asks about an alert → click → detail panel: features, class, confidence
 → professor asks about a feature → answered from the data dictionary
```

This journey defines the UI: a feed, an alert list, two charts, one detail panel — nothing more.
