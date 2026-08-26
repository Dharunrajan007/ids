# Milestone 4 — Multi-Class Model Evaluation (2026-08-26)

The production model: "**which kind** of traffic is this flow — normal, DoS,
Probe, R2L or U2R?" (target `category`). Per ADR-012 the winner of this
milestone is the pipeline the M5 `/predict` endpoint will serve. Everything
below is validation-split evidence only — **KDDTest+ was not touched** and
these numbers must not be quoted as final benchmark performance (see
"Limitations").

## Methodology

- Data: KDDTrain+ only, the SAME stratified 80/20 split as M3
  (**100,778 train / 25,195 validation**, stratified on `category`,
  `RANDOM_STATE = 42`) — binary and multi-class results stay comparable.
- Every candidate = ONE sklearn Pipeline: shared M2 preprocessor + classifier
  (ADR-005), fitted on the training split only.
- Sensible defaults, no hyperparameter search (same M3 scope rule).
  LogisticRegression(max_iter=1000) [convergence, not tuning];
  RandomForestClassifier(n_estimators=100);
  HistGradientBoostingClassifier(defaults — its `early_stopping='auto'`
  reserves a seeded 10% of the *training* split to choose the iteration
  count: training-data-only, so no protocol violation).
- HistGradientBoosting requires dense input, so its pipeline carries a named
  `densify` step after the preprocessor (~97 MB dense; measured, harmless).
  It is the "one additional strong tabular classifier": sklearn-native
  LightGBM-style boosting — no new dependency (XGBoost/LightGBM stay out).
- Reproducibility: the full run was executed **twice**; all metrics and
  confusion matrices were byte-identical (diff excluding timing lines).
  Command: `python -m src.training.train_multiclass`.

## Class distribution (computed fresh from the split, 2026-08-26)

| Class | Full KDDTrain+ | % | Train split | Validation | Imbalance vs normal |
|---|---|---|---|---|---|
| normal | 67,343 | 53.46% | 53,874 | 13,469 | 1.0× |
| dos | 45,927 | 36.46% | 36,741 | 9,186 | 1.5× |
| probe | 11,656 | 9.25% | 9,325 | 2,331 | 5.8× |
| r2l | 995 | 0.79% | 796 | 199 | 67.7× |
| u2r | 52 | 0.041% | 42 | 10 | **1295×** |

Stratification is essentially exact (max drift 0.0023 percentage points).
Two facts that shape everything below:

- **Validation U2R is 10 rows** (8 buffer_overflow, 2 loadmodule — only 2 of
  the 4 training U2R types). U2R recall moves in 10-pp steps, and one row
  changing shifts macro F1 by ~0.5-2 pp. Treat U2R numbers as coarse evidence,
  not precise measurement.
- **Validation R2L is 89% warezclient** (178 of 199). R2L recall is largely
  "warezclient recall"; the other 7 R2L types contribute 21 rows.

## Results

| Model | Accuracy | Macro F1 | Weighted F1 | R2L recall | U2R recall | Missed attacks | False alarms | Train time |
|---|---|---|---|---|---|---|---|---|
| Majority baseline ("always normal") | 0.5346 | 0.1393 | 0.3725 | 0.0 | 0.0 | 11,726 (all) | 0 | — |
| Logistic Regression (standard scaling) | 0.9890 | 0.8559 | 0.9889 | 0.7538 | 0.4000 | 152 | 110 | 14.0 s |
| **Random Forest** (no scaling) | **0.9988** | **0.9500** | **0.9988** | **0.9598** | **0.7000** | **26** | **5** | 4.3 s |
| HistGradientBoosting (no scaling) | 0.9954 | 0.8121 | 0.9959 | 0.9497 | 0.4000 | 39 | 68 | 6.9 s |

"Missed attacks" = any attack row predicted `normal` (the IDS-critical
failure); "false alarms" = normal rows predicted as any attack class.
Prediction: ≤ 0.011 ms/flow in batch for all three (NFR1 allows 200 ms).

Per-class detail, Random Forest (winner): normal P 0.9981 / R 0.9996 ·
dos P 0.9998 / R 0.9999 · probe P 0.9996 / R 0.9940 · r2l P 0.9948 / R 0.9598
· u2r P 0.8750 / R 0.7000.

Confusion matrix — Random Forest (rows = truth, columns = prediction):

|  | normal | dos | probe | r2l | u2r |
|---|---|---|---|---|---|
| **normal** | 13,464 | 2 | 1 | 1 | 1 |
| **dos** | 1 | 9,185 | 0 | 0 | 0 |
| **probe** | 14 | 0 | 2,317 | 0 | 0 |
| **r2l** | 8 | 0 | 0 | 191 | 0 |
| **u2r** | 3 | 0 | 0 | 0 | 7 |

Notable: **every Random Forest error involving an attack is an
attack→normal miss** — it never confuses one attack category with another on
this validation set. Misses are pure missed-intrusion cases, not
mislabeled alerts.

Confusion matrices, other candidates (same row/column order):

- Logistic Regression: normal row 13,359/23/42/45/0 · dos 17/9,167/2/0/0 ·
  probe 84/6/2,238/3/0 · r2l 48/1/0/150/0 · u2r 3/0/0/3/4.
- HistGradientBoosting: normal row 13,401/8/7/18/**35** · dos 0/9,183/0/3/0 ·
  probe 26/0/2,302/3/0 · r2l 9/0/0/189/1 · u2r 4/0/0/2/4.

Train-vs-validation accuracy (overfitting check, R4): LogReg 0.9890 → 0.9890
(no gap) · RF 1.0000 → 0.9988 (0.12 pp — memorization without harmful
in-distribution overfit, same picture as M3) · HGB 0.9970 → 0.9954 (0.16 pp).
The honest generalization test remains KDDTest+, later, once.

## Minority-class analysis (per raw attack label, Random Forest)

- **U2R (10 rows): 7 caught.** buffer_overflow 6/8, loadmodule 1/2. With 42
  training rows total this is evidence the class is *learnable but starved*
  — exactly risk R7, accepted and stated, not hidden.
- **R2L (199 rows): 191 caught.** warezclient 171/178, multihop 1/2;
  guess_passwd 11/11, warezmaster 5/5, phf 2/2, imap 1/1 all caught.
- Probe misses concentrate in slow/stealthy scans: satan 8, portsweep 4,
  ipsweep 1, nmap 1 → predicted normal.
- DoS: 1 miss (a single `land` row) out of 9,186.
- The 5 false alarms spread across all four attack classes (2 dos, 1 probe,
  1 r2l, 1 u2r) — no systematic false-alarm pattern.
- Probability caveat: on U2R rows the forest's top-class probability ranges
  0.40-0.89 (uncalibrated vote fractions) — reported as "confidence" only
  with that caveat (recorded limitation since M1).

Why HistGradientBoosting lost despite 99.5% accuracy: its U2R column is
upside-down — 4 caught (recall 0.40) but **35 normal rows falsely flagged as
u2r** (precision 0.10, F1 0.16). Boosting's additive corrections on a 42-row
class generalize poorly here, and `early_stopping`'s internal split leaves
even fewer minority rows per boosting decision. Its macro F1 (0.8121) ends
up *below* Logistic Regression's despite far better R2L — one collapsed
class dominates an unweighted average over 5 classes. This is macro F1
working as intended: surfacing minority-class failure that weighted metrics
(0.9959) hide completely.

## Selection — DECISION: Random Forest is the M4 multi-class model

Framework (per DoD, in priority order — accuracy alone is never the
criterion; KDDTest+ never consulted):

1. **Macro F1**: RF 0.9500 vs LogReg 0.8559 vs HGB 0.8121 — clear win.
2. **Minority recall/F1**: RF best on both R2L (0.9598/0.9770) and U2R
   (0.7000/0.7778).
3. **Attack detection**: RF misses 26 of 11,726 attacks (binary-view recall
   0.9978 — identical to the M3 binary forest, so moving to 5 classes cost
   nothing in detection).
4. **False positives**: RF 5 vs HGB 68 vs LogReg 110.
5. **Overall**: best accuracy and weighted F1.
6. **Efficiency**: fastest to train here (4.3 s); 11.9 MB artifact;
   38.9 ms single-flow predict through the reloaded artifact (NFR1 ≤ 200 ms).

Random Forest dominates every criterion simultaneously — there was no
trade-off to arbitrate (the A-vs-B scenario of a higher-accuracy model with
worse minority behavior DID occur, but as HGB-vs-LogReg, and the framework
ranks both below RF). Selection used validation data only.

Consistency note (ADR-012): binary "attack" is derived from this model as
`category != "normal"`. On validation that view reproduces the M3 binary
forest's quality exactly (26 FN / 5 FP), confirming one served multi-class
model loses nothing versus serving a separate binary model.

## Serialized artifact

`models/multiclass_pipeline.joblib` (11.9 MB) — the ENTIRE fitted Pipeline
(preprocessor + RandomForest) in one file (ADR-005/009), saved by
`python -m src.training.train_multiclass --save random_forest`.
`models/multiclass_metadata.json` records task, role, classes, config,
RANDOM_STATE, Python/sklearn versions, date, split sizes, all validation
metrics, and single-flow latency — the /health endpoint's model_version
source in M5.
Reload verified: the reloaded artifact reproduced the in-memory model's
predictions on **all 25,195 validation rows** (exact match). The known
joblib-1.5.3-under-NumPy-2.5 DeprecationWarning on load remains harmless
(pinned versions; behavior verified — 43/43 tests pass).

## Limitations (state honestly in the viva)

1. Validation contains only training-known attack types. KDDTest+ adds 17
   unseen types and a much larger R2L share (2,754 rows) — **final scores,
   especially R2L/U2R, will be substantially lower**. Deliberate benchmark
   design, evaluated once at the end.
2. U2R conclusions rest on 10 validation rows of 2 types; R2L is dominated
   by warezclient. Fine-grained minority claims are not supported by this
   split — interpret against 1998-era NSL-KDD imbalance, not modern traffic.
3. `predict_proba` is uncalibrated (RF vote fractions); "confidence" in the
   API carries that caveat.
4. No hyperparameter search or imbalance countermeasures (class weights,
   resampling) were evaluated — deliberately out of scope; a candidate
   improvement to discuss in the viva, not silently added.
