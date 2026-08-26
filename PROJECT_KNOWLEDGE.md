# PROJECT_KNOWLEDGE.md

Single-file project memory. A new contributor (or a future AI session) should be able
to work on this project from this file + the docs it links, with zero chat history.

Last updated: 2026-08-26 (Milestone 3 complete: binary baseline = Random Forest).

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
- [x] M1 closeout (2026-08-26) — ADR-012 approved; src/ is a package (`python -m src.*`);
      requirements pinned (Python 3.14); RANDOM_STATE=42; evaluation protocol recorded
      (risk-register.md); M2 preprocessing decisions recorded (docs/preprocessing-decisions.md).
      Still pending: GitHub remote + milestone-1 tag (user action).
- [x] M2 preprocessing pipeline (2026-08-26) — `src/preprocessing/` package + 21-test
      pytest suite (ADR-013); DoD checklist complete; see "Preprocessing layer" below
- [x] M3 binary baseline (2026-08-26) — Random Forest selected over LogReg and
      majority baseline on the validation split; serialized as one pipeline;
      full results + rationale in docs/m3-binary-evaluation.md
- [ ] M4 multi-class + comparison → M5 API → M6 dashboard
      → M7 simulator/demo → M8 docs → M9 (optional) CICIDS2017

## Important decisions (full reasoning in docs/DECISIONS.md)

ADR-001 NSL-KDD over CICIDS2017 · ADR-002 scikit-learn · ADR-003 FastAPI ·
ADR-004 React/Vite/Recharts · ADR-005 one serialized Pipeline for train/serve parity ·
ADR-006 replay simulator, no capture · ADR-007 polling · ADR-008 in-memory bounded
history · ADR-009 joblib · ADR-010 Phase 0 frozen (changes = new ADRs) ·
ADR-011 `# %%` .py exploration files, not .ipynb ·
ADR-012 `/predict` serves the multi-class pipeline only (approved 2026-08-26).

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
- Data re-downloadable via `python -m src.download_data` (row-count integrity check).
- Citation owed in report: Tavallaee, Bagheri, Lu, Ghorbani, "A Detailed Analysis of
  the KDD CUP 99 Data Set", IEEE CISDA 2009 (University of New Brunswick).

## Model facts

**M3 binary baseline (done, 2026-08-26 — full numbers in docs/m3-binary-evaluation.md):**
Random Forest (100 trees, defaults, RANDOM_STATE) selected. Validation:
accuracy 0.9988, attack recall 0.9978 (26 FN), attack precision 0.9996 (5 FP),
macro F1 0.9988 — vs LogisticRegression 0.9736 acc (415 FN / 251 FP) and
majority baseline 0.5346 acc (catches nothing). Artifact:
models/binary_pipeline.joblib (8.3 MB, preprocessor+classifier in ONE pipeline)
+ binary_metadata.json; reload reproduces all 25,195 validation predictions
exactly; metrics identical across two full runs. Train 14.7 s (NFR1 ok).
Role per ADR-012: evaluated baseline only — never served by the API.
Validation contains only training-known attack types; KDDTest+ (17 unseen
types) stays untouched until the final locked evaluation and WILL score lower.

M4 next: multi-class comparison of 2-3 algorithms, winner serialized with
preprocessing as one Pipeline → becomes the production model.
Evaluation protocol (binding, full text in docs/risk-register.md):
all selection/tuning on stratified KDDTrain+ validation/CV — stratified on the
5-way `category` even for the binary task; KDDTest+ evaluated exactly once after
all choices are locked; every stochastic step uses `RANDOM_STATE = 42`
(src/config.py). Preprocessing decisions for M2 (targets, drops, encoding,
su_attempted 2→1 recode, scaling trade-offs) are frozen in
docs/preprocessing-decisions.md. Metrics: confusion matrix, per-class
precision/recall/F1. `predict_proba` "confidence" is uncalibrated — caveat in report.

## Preprocessing layer (M2 — verified by tests/, decisions in docs/preprocessing-decisions.md)

`src.preprocessing` public API:
- `split_features_target(df, task)` — task `"binary"` (y=`is_attack`) or
  `"multiclass"` (y=`category`). X = the 40 allow-listed features; `label`,
  `difficulty`, targets, and `num_outbound_cmds` are excluded by construction.
- `build_preprocessor(scaling=...)` — `"none"` (trees) or `"standard"`
  (scale-sensitive); MinMax rejected. OneHotEncoder(handle_unknown="ignore") on
  protocol_type/service/flag; `su_attempted` 2→1 domain repair as a named,
  joblib-safe step. 121 output features when fitted on the training split.
- `train_validation_split(df)` — KDDTrain+ only, 80/20, stratified on 5-way
  `category` (U2R: 42 train / 10 validation), RANDOM_STATE, reproducible.

Rule: fit on the training split only; validation is transformed with the fitted
object; KDDTest+ untouched (a source-scan test enforces src/preprocessing
cannot read it). Run the suite with `python -m pytest` (21 tests, ~30 s).

## API endpoints (contract frozen — docs/api-contract.md)

- `POST /predict` → `{prediction, attack_type, confidence, timestamp}`
- `GET /stats` → counters + attacks_by_type + traffic_timeline
- `GET /predictions/recent?limit=50` → feed items (response + submitted features)
- `GET /health` → `{status, model_loaded, model_version}`

ADR-012 (approved 2026-08-26): the production `/predict` serves the multi-class
pipeline ONLY — prediction = "attack" iff category != "normal", attack_type =
category (null when normal). The binary model stays as the M3 evaluated baseline
and is never loaded by the API.

## Folder structure

```
ids/
├── PROJECT_KNOWLEDGE.md   ← this file
├── README.md · requirements.txt · .gitignore
├── data/raw|processed/    (gitignored, .gitkeep)
├── docs/                  requirements · api-contract · DECISIONS · risk-register ·
│                          definition-of-done · data-dictionary · preprocessing-decisions
├── models/                (.joblib gitignored)
├── notebooks/01_data_exploration.py   (# %% cells)
├── src/                   __init__.py · config.py · download_data.py · data_loader.py
│   │                      (package: run via `python -m src.<module>` from the root)
│   ├── preprocessing/     pipeline.py (column roles, build_preprocessor,
│   │                      su_attempted repair) · split.py (stratified split)
│   ├── training/          binary.py (pipelines + baseline) · train_binary.py runner
│   └── evaluation/        metrics.py (confusion matrix, per-class P/R/F1)
├── tests/                 conftest.py (shared fixtures) · test_preprocessing.py ·
│                          test_training_binary.py (+ root conftest.py)
├── api/ · simulator/      (.gitkeep, empty until M5/M7)
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
No critical defects. Must-fix before M2 — status at closeout (2026-08-26):
1. ✅ DONE — src/ is a real package (`src/__init__.py`, `from src.config import ...`,
   `python -m src.download_data`); notebook imports via project root, no src/-path hack.
2. ✅ DONE — requirements.txt pinned (pandas 3.0.5, numpy 2.5.1, scikit-learn 1.9.0,
   matplotlib 3.11.1, joblib 1.5.3, ipykernel 7.3.0); "Python 3.14" stated in
   README + requirements.txt.
3. ✅ DONE — ADR-012 approved and recorded in docs/DECISIONS.md.
4. ✅ DONE — `RANDOM_STATE = 42` in config.py; evaluation protocol (KDDTest+ once,
   selection on stratified 5-way validation/CV) recorded in risk-register.md.
5. ⏳ PENDING (user action) — push to a private GitHub remote; `git tag milestone-1`
   (tracked as risk R10). Commit-per-logical-unit is in effect from the closeout commit.
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
