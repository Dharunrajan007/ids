# Milestone 2 Preprocessing Decisions

Recorded at the Milestone-1 closeout (2026-08-26), **before** any preprocessing
code exists, so M2 implements decisions instead of making them mid-code.
All numbers below were computed from the actual dataset files, not assumed.
The pipeline itself (ColumnTransformer + Pipeline) is built in Milestone 2 —
nothing here is implemented yet.

## 1–2. Targets

| Task | Target column | Notes |
|---|---|---|
| Binary model (FR2, M3) | `is_attack` | 0 = normal, 1 = attack; derived by `src.data_loader` |
| Multi-class model (FR3, M4) | `category` | normal / dos / probe / r2l / u2r; the production model per ADR-012 |

## 3. Columns that must NEVER be model features

`label`, `is_attack`, `category` (they ARE the answer — using them is target
leakage) and `difficulty` (encodes how hard reference classifiers found the
row — direct evaluation leakage). The M2 code must drop all four before the
feature matrix is built, and the M2 review checks this explicitly (risk R3).

## 4. Dropped feature

`num_outbound_cmds` — constant 0 across all 125,973 train and 22,544 test rows;
zero information (verified in M1 EDA).

## 5. Categorical features

`protocol_type` (3 values) · `service` (70) · `flag` (11) — one-hot encoded.
All other features are numeric and pass through the encoder untouched.

## 6. Unknown categorical values

`OneHotEncoder(handle_unknown="ignore")`. M1 EDA verified the test set contains
no categorical value absent from train, so this never triggers on NSL-KDD —
but the API (M5) can receive arbitrary strings, and "ignore" (all-zeros row for
that feature block) beats a 500 error at serve time (NFR6).

## 7. `su_attempted` out-of-spec value 2 — DECISION: recode 2 → 1, inside the pipeline

Inspection (2026-08-26, both splits):

| Value | Train rows | Test rows | Labels of those rows |
|---|---|---|---|
| 0 | 125,893 | 22,540 | everything else |
| 1 | 21 | 2 | train: 20 normal, 1 spy · test: 1 normal, 1 httptunnel |
| 2 | 59 | 2 | **all `normal`** — and every one has `root_shell=1`, `logged_in=1` |

The documented domain is {0, 1} ("was `su root` attempted"). Every value-2 row
is a logged-in session that obtained a root shell — value 2 almost certainly
meant "attempted **and succeeded**" in the original collection. Decision:

- **Recode 2 → 1** as an explicit, named transformation step inside the M2
  pipeline (never by editing the raw files — R6, and never silently).
- Why 1 and not 0 (the common literature shortcut): "su was attempted" is
  factually TRUE for these rows; 2 → 0 would assert it never happened.
- Why recode at all: left as-is, a tree can memorize the artifact rule
  `su_attempted == 2 → normal`, an inexplicable dataset quirk (bad for NFR4).
- Impact is negligible either way (61 rows of 148,517); this is about
  explainability and staying within the documented feature semantics.

## 8. Scaling — StandardScaler vs MinMaxScaler vs none

Context from M1 EDA: feature scales span 9 orders of magnitude
(`src_bytes` max 1.38 billion, median ~0, heavy-tailed; rate features in [0,1]).

| Option | Behaviour on this data | Verdict |
|---|---|---|
| No scaling (tree models) | Trees split on thresholds — monotonic transforms change nothing; raw units keep feature importances interpretable | **Use for tree models** (RandomForest etc.) |
| StandardScaler | Preserves outlier structure; heavy tails mean extreme rows land at z ≈ hundreds, but the [0,1] bulk stays usable and no information is destroyed | **Use for scale-sensitive models** (LogisticRegression, kNN, SVM) |
| MinMaxScaler | One 1.38-billion outlier squashes ~all other `src_bytes` values into ≈[0, 1e-7] — the feature's bulk becomes numerically invisible | Rejected for this data |

Decision: the ColumnTransformer's numeric branch includes StandardScaler only
in pipeline variants for scale-sensitive models; tree pipelines pass numerics
through unscaled. Whichever model wins M4 is serialized WITH exactly the
preprocessing it was trained with (ADR-005) — so this choice never leaks into
serving as an inconsistency. A log1p transform for the byte-count features may
be *evaluated* in M2/M3 as a documented experiment, but is not decided here.

## Evaluation guardrails (binding — full protocol in risk-register.md)

Splits are stratified on the 5-way `category`; all selection happens on
KDDTrain+ validation/CV; KDDTest+ is evaluated exactly once at the end;
every stochastic step uses `RANDOM_STATE = 42` from `src/config.py`.
