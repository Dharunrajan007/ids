# Definition of Done

A milestone is complete **only** when every item on its checklist is checked.
Generic items apply to all milestones; specific items are added when the milestone starts.

## Generic (every milestone)

- [ ] Code runs end-to-end without errors on this machine
- [ ] No TODO/FIXME comments left in committed code
- [ ] README project-status section updated
- [ ] New decisions recorded as ADRs in DECISIONS.md
- [ ] Risk register statuses reviewed/updated
- [ ] Work committed to git with a meaningful message
- [ ] Reproducible: would work on a fresh clone following the README

## Milestone 1 — setup & data exploration

- [x] Folder skeleton created, git initialized
- [x] Phase 0 documents committed to docs/
- [x] Virtual environment + dependencies installable from requirements.txt
- [x] NSL-KDD train and test sets downloaded via a repeatable script (not manual clicks)
- [x] Data loads correctly with named columns (shape and label distribution verified)
- [x] Exploration notebook produces class distribution + basic feature stats
- [x] Data dictionary filled for all 41 features + label columns

## Milestone 2 — preprocessing pipeline

- [x] Feature/target separation: `label`, `difficulty`, `is_attack`, `category`
      excluded from the feature matrix by construction (allow-list selection)
- [x] `num_outbound_cmds` dropped
- [x] `su_attempted` domain repair (2 → 1) implemented inside the preprocessing
      pipeline as a named, serializable step; raw dataset files untouched
- [x] Categorical encoding: `OneHotEncoder(handle_unknown="ignore")` on
      `protocol_type`, `service`, `flag`; unseen values transform to zeros, no crash
- [x] Scaling selectable per model family: `"none"` (trees) / `"standard"`
      (scale-sensitive); MinMaxScaler rejected with an explanatory error
- [x] Reusable train/validation split: KDDTrain+ only, stratified on the 5-way
      `category`, `RANDOM_STATE`, reproducible, U2R represented in both halves
- [x] Leakage guards verified: preprocessor fits on the training split only;
      validation transformed without refitting; no `src/preprocessing` code can
      read KDDTest+ (enforced by a source-scan test)
- [x] Automated test suite (pytest, ADR-013) covering all of the above — 21 tests passing
- [x] Docs updated: README, PROJECT_KNOWLEDGE.md, risk register reviewed

## Milestone 3 — binary baseline model

- [x] Majority-class baseline computed on the validation split: accuracy,
      meaningful per-class metrics, confusion matrix — the reference floor
- [x] LogisticRegression pipeline = `build_preprocessor(scaling="standard")` +
      classifier, `RANDOM_STATE`, sensible default config, trained on the
      100,778-row training split ONLY
- [x] RandomForest pipeline = `build_preprocessor(scaling="none")` + classifier,
      `RANDOM_STATE`, sensible default config, same training split
- [x] All evaluation on the 25,195-row validation split ONLY: confusion matrix,
      accuracy, per-class precision/recall/F1, macro + weighted averages,
      training/prediction times
- [x] Comparison table (baseline + both models) and a documented selection
      decision based on validation performance and IDS priorities (attack recall
      weighed against false positives) — never accuracy alone, never KDDTest+
      → Random Forest selected (docs/m3-binary-evaluation.md)
- [x] Selected pipeline serialized with joblib as ONE artifact (preprocessing +
      classifier) in models/, with a metadata file (model type, date, versions,
      configuration, validation metrics)
- [x] Reload verified: artifact loads, predicts on validation samples, output is
      binary, predictions identical to pre-save (all 25,195 rows)
- [x] pytest tests: pipeline construction, training + prediction, binary output
      domain, no invalid outputs, save/reload consistency, KDDTest+ source-scan
      isolation for src/training + src/evaluation — 31 tests passing
- [x] Leakage audit passed and reproducibility demonstrated: two runs →
      identical metrics (diff excluding timing lines)
- [x] Docs updated: M3 results doc, README status, PROJECT_KNOWLEDGE, risk
      register review; NFR1 timing recorded (train 14.7 s, predict ≪ 200 ms)

## Milestone 4 — multi-class model (the production candidate, ADR-012)

DATA
- [x] Target = 5-way `category` (normal/dos/probe/r2l/u2r) via
      `split_features_target(df, "multiclass")`; M2 preprocessing reused
      unchanged; same stratified 80/20 split as M3 (100,778 / 25,195,
      `RANDOM_STATE = 42`); KDDTest+ never read (source-scan test covers all
      of src/training + src/evaluation automatically)
- [x] Fresh class-distribution analysis recorded (counts, percentages,
      imbalance ratios, stratification check, per-label minority breakdown)

BASELINE
- [x] Majority-class baseline ("always normal") evaluated with the full
      metric set — the floor every model must clearly beat

MODELS — 3 candidates, each ONE sklearn Pipeline (preprocessor + classifier),
sensible defaults, no hyperparameter search (same M3 rule), `RANDOM_STATE`
- [x] LogisticRegression (scaling="standard", max_iter=1000) — linear
      reference; native multinomial in sklearn
- [x] RandomForestClassifier (scaling="none", 100 trees) — M3 winner,
      natively multi-class
- [x] HistGradientBoostingClassifier (scaling="none" + named densify step —
      it requires dense input) — sklearn-native gradient boosting, the
      strongest classical tabular family; no external dependency (no
      XGBoost/LightGBM, per scope rules)

EVALUATION — validation split ONLY, for every candidate
- [x] 5×5 confusion matrix, accuracy, per-class precision/recall/F1,
      macro + weighted averages, training time, prediction time
- [x] Train-vs-validation accuracy gap recorded (overfitting check, R4)

MINORITY-CLASS ANALYSIS
- [x] Explicit R2L and U2R analysis: which rows were caught/missed and as
      what; stated caveats — validation U2R is only 10 rows (2 of 4 types),
      validation R2L is 89% warezclient; poor results reported, not hidden

MODEL SELECTION — documented framework, in priority order:
      (1) macro F1, (2) minority-class recall/F1 (R2L, U2R),
      (3) attack detection quality (normal-row confusion / missed attacks),
      (4) false-positive behavior, (5) overall performance,
      (6) computational efficiency. Accuracy alone is never the criterion;
      KDDTest+ is never consulted.
- [x] Selection recorded with reasoning defensible to an examiner

SERIALIZATION
- [x] Selected pipeline serialized as ONE joblib artifact
      (models/multiclass_pipeline.joblib) + metadata JSON (model name, task,
      classes, config, RANDOM_STATE, Python/sklearn versions, date,
      validation metrics, feature/preprocessing info)
- [x] Reload verified: predictions before save == predictions after reload
      on all 25,195 validation rows

VERIFICATION
- [x] pytest coverage: pipeline construction per family, training +
      prediction, 5-class output domain, probability validity, save/reload
      consistency, KDDTest+ isolation; full suite green
- [x] Full M4 run executed at least twice: metrics, confusion matrices and
      selected model identical (diff excluding timing lines)
- [x] Adversarial review pass (leakage, misuse of metrics, unknown
      categoricals, docs-vs-code drift, M3 regression) with findings fixed

DOCS
- [x] docs/m4-multiclass-evaluation.md written; definition-of-done, README,
      PROJECT_KNOWLEDGE, risk register updated; U2R/R2L results interpreted
      in light of extreme imbalance and dataset age

## Milestone 5 — FastAPI prediction service (contract: docs/api-contract.md)

SERVICE
- [x] FastAPI app in api/ (main.py, schemas.py, model_service.py, state.py);
      Uvicorn starts it; automatic /docs works
- [x] models/multiclass_pipeline.joblib + multiclass_metadata.json loaded
      exactly ONCE at application startup (never per request); the M3 binary
      artifact is never loaded (ADR-012)
- [x] Request schema = the exact 40-feature M2 allow-list, DERIVED from
      src.preprocessing.FEATURE_COLUMNS (single source of truth — cannot
      drift); 3 categorical fields typed str, 37 numeric typed float;
      extra/missing/invalid fields → HTTP 422 (NFR6); unknown categorical
      VALUES pass through safely (M2 handle_unknown="ignore")
- [x] POST /predict: ADR-012 mapping (normal → prediction "normal" +
      attack_type null; else "attack" + category), confidence =
      max predict_proba (documented as UNCALIBRATED), API-generated UTC
      timestamp; no preprocessing logic duplicated in API code
- [x] GET /stats: total_flows, normal_count, attack_count, attacks_by_type,
      per-minute traffic_timeline
- [x] GET /predictions/recent?limit=50: newest first, default 50, enforced
      maximum, each record = response fields + submitted features
- [x] GET /health: status, model_loaded, model_version from the metadata
      artifact (model_name-saved_date); never runs prediction
- [x] Bounded in-memory state (ADR-008), documented sizes: last 1,000
      records, 60-minute timeline window, lifetime counters; thread-safe;
      resets on restart (intentional)
- [x] CORS restricted to the Vite dev origins (localhost/127.0.0.1:5173),
      not "*" — documented

VERIFICATION
- [x] Dedicated pytest suite: startup, health, all five category mappings,
      confidence/timestamp validity, 422 behavior, unknown-categorical
      safety, response schema, stats zero-state + update, recent + limit +
      max-limit, bounded history, single model load, M4-artifact identity,
      M3-not-used, KDDTest+ isolation for api/, error handling
- [x] Full suite green (M1-M5); M3/M4 runners unaffected
- [x] ACTUAL API latency measured (startup, warm single, repeated) and
      recorded; NFR1 single prediction < 200 ms verified
- [x] Manual verification against a running Uvicorn: /health, /predict with
      a real KDDTrain+ validation row (request-path testing only — never
      model evaluation), /stats, /predictions/recent, /docs
- [x] Adversarial audit (malformed input, repeated loading, unbounded
      growth, stats consistency, contract drift, CORS, isolation) passed

DOCS
- [x] README (run instructions + status), PROJECT_KNOWLEDGE, risk register
      reviewed; api-contract clarifications recorded if needed
