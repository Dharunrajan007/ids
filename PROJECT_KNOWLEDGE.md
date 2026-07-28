# PROJECT_KNOWLEDGE.md

Single-file project memory. A new contributor (or a future AI session) should be able
to work on this project from this file + the docs it links, with zero chat history.

Last updated: 2026-07-28 (after the Milestone-1 external review).

## What this project is

AI-powered Intrusion Detection System — a **college project** by a beginner student
learning cybersecurity. Classifies NSL-KDD network flows as normal vs attack (binary)
and by attack category (DoS / Probe / R2L / U2R). Explicitly **not** a commercial
product; optimized for learning, explainability, and a smooth viva demo.

**Taxonomy position:** ML-based **misuse detection** (supervised, trained on labeled
attacks). Not signature matching, not anomaly detection (it does not model normal
traffic alone). It is an IDS (detect + alert), not an IPS (no blocking).

## Architecture

```
OFFLINE:  NSL-KDD → preprocessing (inside sklearn Pipeline) → training → pipeline.joblib
ONLINE:   simulator (replays KDDTest+ rows) → FastAPI /predict → React dashboard (2s polling)
```

Key invariant (ADR-005): ALL preprocessing lives inside the single serialized
Pipeline, so train-time and serve-time transformations cannot drift.

## Technology stack (fixed by ADRs — do not change without a new ADR)

Python 3.14 · pandas · scikit-learn · matplotlib · FastAPI + Uvicorn (M5) ·
React + Vite + Recharts (M6) · joblib · git. No DB, no auth, no Docker, no queues,
no websockets (polling), no packet capture (replay simulator).

## Milestone status

- [x] Phase 0 — requirements, API contract, ADRs, risk register, DoD (frozen 2026-07-28)
- [x] Milestone 1 — skeleton, git, venv, dataset download + EDA, data dictionary (commit 4bc7471)
- [x] External review of M1 state (5 reviewers + adversarial verification, 2026-07-28) — see "Review outcomes" below
- [ ] M2 preprocessing pipeline → M3 binary baseline → M4 multi-class + comparison
      → M5 API → M6 dashboard → M7 simulator/demo → M8 docs → M9 (optional) CICIDS2017

## Important decisions (full reasoning in docs/DECISIONS.md)

ADR-001 NSL-KDD over CICIDS2017 · ADR-002 scikit-learn · ADR-003 FastAPI ·
ADR-004 React/Vite/Recharts · ADR-005 one serialized Pipeline for train/serve parity ·
ADR-006 replay simulator, no capture · ADR-007 polling · ADR-008 in-memory bounded
history · ADR-009 joblib · ADR-010 Phase 0 frozen (changes = new ADRs) ·
ADR-011 `# %%` .py exploration files, not .ipynb.

## Dataset facts (verified against the actual files, 2026-07-28)

- KDDTrain+: 125,973 rows; KDDTest+: 22,544 rows; 41 features + label + difficulty.
- Train: 53.5% normal / 46.5% attack. Test: 43.1% normal / **56.9% attack**.
- Categories (train → test): DoS 45,927→7,458 · Probe 11,656→2,421 ·
  R2L 995→**2,754** · U2R **52**→200. Extreme category imbalance is a data property.
- **17 attack types appear only in the test set** (deliberate generalization test);
  test scores WILL be worse than validation scores — expected, reported honestly.
- No categorical values in test are absent from train (train has 6 services test lacks).
- `num_outbound_cmds` is constant 0 → drop in M2. `difficulty` is dropped (leaks
  evaluation info). `su_attempted` contains out-of-spec value 2 (59 train rows) —
  known dataset anomaly, recode decision due in M2.
- `httptunnel` → U2R mapping is contested in literature (DARPA-1999 says R2L); kept
  as U2R to match canonical NSL-KDD counts. It is 133 of 200 test U2R rows, so U2R
  recall ≈ httptunnel recall.
- Data re-downloadable via `python src\download_data.py` (row-count integrity check).
- Citation owed in report: Tavallaee, Bagheri, Lu, Ghorbani, "A Detailed Analysis of
  the KDD CUP 99 Data Set", IEEE CISDA 2009 (University of New Brunswick).

## Model facts

No model trained yet (starts M3). Planned: binary baseline (M3), then multi-class
comparison of 2-3 algorithms (M4), winner serialized with preprocessing as one
Pipeline. Evaluation: confusion matrix, per-class precision/recall/F1, on a
stratified validation split AND official KDDTest+ (touched once, after all choices).
`predict_proba` "confidence" is uncalibrated — caveat in report.

## API endpoints (contract frozen — docs/api-contract.md)

- `POST /predict` → `{prediction, attack_type, confidence, timestamp}`
- `GET /stats` → counters + attacks_by_type + traffic_timeline
- `GET /predictions/recent?limit=50` → feed items (response + submitted features)
- `GET /health` → `{status, model_loaded, model_version}`

Pending decision (proposed ADR-012, awaiting user approval): serve the multi-class
pipeline ONLY — prediction = "attack" iff category != "normal"; removes any
binary/multi-class disagreement; binary model stays as the M3 evaluated baseline.

## Folder structure

```
ids/
├── PROJECT_KNOWLEDGE.md   ← this file
├── README.md · requirements.txt · .gitignore
├── data/raw|processed/    (gitignored, .gitkeep)
├── docs/                  requirements · api-contract · DECISIONS · risk-register ·
│                          definition-of-done · data-dictionary
├── models/                (.joblib gitignored)
├── notebooks/01_data_exploration.py   (# %% cells)
├── src/                   config.py · download_data.py · data_loader.py
│   └── preprocessing|training|evaluation/   (empty until M2-M4)
├── api/ · simulator/      (empty until M5/M7)
└── dashboard/             (does not exist until M6)
```

## Known limitations (state honestly in the report/viva)

1. 1998-era dataset; content features (root_shell etc.) existed only because DARPA
   traffic was plaintext + host-audited — impossible for a modern network-only IDS.
2. Demo traffic is a replay of KDDTest+ (~57% attacks — benchmark artifact, not a
   realistic base rate; narrate this during the demo).
3. U2R will have poor recall (52 training rows) — acknowledged, not hidden.
4. Detection only; no prevention. Localhost only. History resets on API restart.

## Open risks (full table: docs/risk-register.md)

R1 misleading accuracy · R3 leakage (fit on train only) · R4 overfitting (stratified
CV) · R5 React friction · R7 U2R rarity (accepted) · R9 demo-day breakage.
Review added: no git remote (single-laptop copy), unpinned dependencies, no seed
policy, no timeline/deadline recorded.

## Review outcomes (2026-07-28, 11-agent external review, findings verified)

Scores: Cybersecurity 9 · Documentation 9 · ML 8.5 · Code quality 8.5 · Architecture 8.
No critical defects. Must-fix before M2 (awaiting user approval):
1. Make src/ a real package (`src/__init__.py`, `from src.config import ...`,
   `python -m src.download_data`) — flat imports break the moment api/ imports src/ (M5).
2. Pin requirements.txt versions + state "Python 3.14" + add ipykernel; joblib compat
   across sklearn versions is why this matters (save-in-M3 → load-in-M5).
3. ADR-012 (multi-class-only serving, above).
4. Add `RANDOM_STATE = 42` to config.py; rule: KDDTest+ evaluated once, all
   selection on stratified validation/CV.
5. Push to a private GitHub remote; `git tag milestone-1`; commit per logical unit
   from now on.
Should-fix (M2-M5 windows): dataset citation, IDS-taxonomy paragraph, CORS note,
OneHotEncoder(handle_unknown='ignore'), tests/ plan + DoD lines, DoD generic-items
wording, timeline with real demo date, httptunnel/su_attempted notes, model metadata
alongside the joblib (feeds /health model_version).

## Lessons learned

1. Freezing requirements before code prevented redesign churn — but committing docs
   and code together made the freeze unverifiable in git history; commit granularity
   matters as much as the freeze itself.
2. Verify every documented number against the actual data — every EDA claim survived
   adversarial review because it was computed, not copied.
3. Script-style flat imports feel fine until a second package needs the code;
   package structure is cheapest on day one.
4. Reproducibility is three controls: pinned versions, verified data, fixed seeds.
