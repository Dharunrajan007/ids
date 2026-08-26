# Milestone 3 — Binary Model Evaluation (2026-08-26)

The first ML detector: "is this flow **normal** or an **attack**?"
(target `is_attack`). Everything below is validation-split evidence only —
**KDDTest+ was not touched** and these numbers must not be quoted as final
benchmark performance (see "Limitations").

## Methodology

- Data: KDDTrain+ only, split 80/20 → **100,778 train / 25,195 validation**,
  stratified on the 5-way `category`, `RANDOM_STATE = 42` (evaluation
  protocol, docs/risk-register.md).
- Every model = ONE sklearn Pipeline: shared M2 preprocessor + classifier
  (ADR-005). Preprocessing fitted on the training split only.
- Configurations are sensible defaults — no hyperparameter search (M3 scope).
  LogisticRegression(max_iter=1000) [raised only so the solver converges;
  it did converge — no warnings]; RandomForestClassifier(n_estimators=100).
- Reproducibility: the full run was executed **twice**; all metrics were
  byte-identical (diff excluding timing lines). Command:
  `python -m src.training.train_binary`.

## Results

| Model | Accuracy | Attack precision | Attack recall | Attack F1 | Macro F1 | Weighted F1 | Train time |
|---|---|---|---|---|---|---|---|
| Majority baseline ("always normal") | 0.5346 | 0.0 | **0.0** | 0.0 | 0.3484 | 0.3725 | — |
| Logistic Regression (scaling="standard") | 0.9736 | 0.9783 | 0.9646 | 0.9714 | 0.9734 | 0.9736 | 7.7 s |
| Random Forest (scaling="none") | **0.9988** | **0.9996** | **0.9978** | **0.9987** | **0.9988** | **0.9988** | 14.7 s |

Confusion matrices (rows = truth, columns = prediction), validation split
(13,469 normal / 11,726 attack):

| | Baseline | Logistic Regression | Random Forest |
|---|---|---|---|
| normal → (normal, attack) | 13,469 / 0 | 13,218 / **251 FP** | 13,464 / **5 FP** |
| attack → (normal, attack) | **11,726 FN** / 0 | **415 FN** / 11,311 | **26 FN** / 11,700 |

Per-class detail — Logistic Regression: normal P 0.9696 / R 0.9814 / F1 0.9754;
attack P 0.9783 / R 0.9646 / F1 0.9714. Random Forest: normal P 0.9981 /
R 0.9996 / F1 0.9989; attack P 0.9996 / R 0.9978 / F1 0.9987.

Train-split vs validation accuracy (overfitting check, risk R4):
LogReg 0.9734 → 0.9736 (no gap); RF **1.0000** → 0.9988. The forest memorizes
its training data perfectly — normal for unconstrained forests — but the tiny
validation gap (0.12 pp) shows this is not harmful *within* the known attack
distribution. The honest generalization test is KDDTest+ with its 17 unseen
attack types, later.

## Why the baseline matters

"Always predict normal" scores 53.5% accuracy while catching **zero of
11,726 attacks** — an IDS that never detects anything. Any reported accuracy
only means something relative to this floor, and it is why this project never
reports accuracy without per-class recall (risk R1).

## Reading the results (IDS view)

- **False negative (FN)** = a real attack called normal — a missed intrusion,
  the worst outcome for an IDS. Attack **recall** measures exactly this:
  LogReg missed 415 attacks (recall 0.9646); the forest missed 26 (0.9978).
- **False positive (FP)** = normal traffic flagged as attack — a false alarm
  that erodes trust in the alert feed. LogReg raised 251; the forest 5.
- Why they differ: logistic regression can only draw one straight boundary
  through the 121-dimensional feature space; attacks that look "mostly normal"
  end up on the wrong side. The forest's voting trees carve out specific
  combinations (e.g. *this* service with *this* error-rate pattern), which
  suits tabular flow data with categorical structure.

## Selection — DECISION: Random Forest is the M3 binary baseline

Rule (per DoD): validation performance + IDS priorities — attack recall
weighed against false positives, never accuracy alone, never KDDTest+.

- Random Forest wins on **both** IDS priorities simultaneously: 16× fewer
  missed attacks (26 vs 415) *and* 50× fewer false alarms (5 vs 251) — there
  is no trade-off to arbitrate; it dominates every recorded metric.
- Cost is acceptable: 14.7 s training (NFR1 allows 10 min), 0.011 ms/flow
  prediction (NFR1 allows 200 ms), 8.3 MB artifact.
- Logistic regression is NOT discarded from the project narrative: it is the
  explainable linear reference and confirms the task is largely, but not
  perfectly, linearly separable (97.4%).

Role reminder (ADR-012): this binary model is the M3 **evaluated baseline**
for learning and comparison. The production `/predict` endpoint will serve
the multi-class pipeline selected in M4.

## Serialized artifact

`models/binary_pipeline.joblib` (8.3 MB) — the ENTIRE fitted Pipeline
(preprocessor + RandomForest) in one file, saved with joblib (ADR-009) by
`python -m src.training.train_binary --save random_forest`.
`models/binary_metadata.json` records model, date, Python/sklearn versions,
config, split sizes, and all validation metrics.
Reload verified: the reloaded artifact reproduced the in-memory model's
predictions on **all 25,195 validation rows** (exact match), and the
preprocessing vocabulary travels inside the artifact.
Note: joblib 1.5.3 emits a harmless upstream DeprecationWarning under
NumPy 2.5 during load; pinned versions keep behavior correct (verified).

## Limitations (state honestly in the viva)

1. Validation contains only attack types the model saw in training. KDDTest+
   adds 17 unseen types, so **final scores will be lower** — deliberate
   benchmark design, evaluated once at the end.
2. 99.88% is a *validation* number on 1998-era benchmark data — not a claim
   about real-world traffic.
3. `predict_proba` confidence is uncalibrated (recorded caveat).
4. Binary view hides per-category weakness: R2L/U2R detection quality is
   invisible inside "attack" and is exactly what M4's multi-class evaluation
   will expose.
