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

## Milestone 6 — React dashboard (stack frozen by ADR-004; polling by ADR-007)

APP
- [x] dashboard/ = React + Vite + Recharts, plain fetch, no state-management
      library, no WebSockets/database/auth (frozen scope); Vite pinned to
      port 5173 with strictPort (the API's CORS allows exactly that origin —
      a silent port shift would break the app confusingly)
- [x] Polls the real FastAPI service every 2 s (/stats + /predictions/recent,
      ADR-007; /health on a slower cadence — it never changes mid-run);
      timer-chained polling with cleanup: no overlapping requests, no
      duplicated timers, no leaks after unmount
- [x] No KDDTest+ access (frontend code touches no dataset files at all)

UI — professional IDS/SOC visual language, clear normal-vs-attack distinction
- [x] Header: project title, live API/model status from /health
      (model_version shown), connection indicator
- [x] Counters: total flows, normal, attacks (from /stats)
- [x] Traffic-over-time chart (per-minute normal vs attack, /stats timeline)
- [x] Attack-category breakdown chart (attacks_by_type)
- [x] Live prediction feed (newest first, from /predictions/recent)
- [x] Attack alerts section (attack rows only), clickable
- [x] Detail panel for a selected record: prediction, attack type,
      confidence (labeled as the model's UNCALIBRATED probability),
      timestamp, and the submitted features
- [x] States handled without crashing: initial loading, API disconnected
      (banner + retry, last data kept), empty history, malformed/unknown
      values (unknown attack categories render safely; React's default
      escaping only — no dangerouslySetInnerHTML)
- [x] Responsive layout (usable at laptop and half-screen widths);
      no excessive animation, no feature bloat

VERIFICATION
- [x] `npm run build` succeeds
- [x] Unit tests for the dashboard's pure logic (formatting, chart-data
      shaping, alert filtering) pass via vitest
- [x] Live integration against the real running FastAPI service: load,
      polling cadence, counters/charts/feed update, alert click → details,
      disconnect handling verified
- [x] Adversarial review (contract mismatch, timer leaks, race conditions,
      empty/invalid data, CORS, rendering safety, M1-M5 regression) passed
- [x] Full Python suite still green (M1-M5 untouched)

DOCS
- [x] README (run instructions + status), PROJECT_KNOWLEDGE, risk register
      updated; new ADRs only if a genuine architectural decision arose

## Milestone 7 — traffic simulator + end-to-end demo (ADR-006: replay, no capture)

SIMULATOR — simulated traffic replay through the same prediction API path
(never to be called "live network detection")
- [x] simulator/ package: reads KDDTest+ rows via the existing loader
      WITHOUT modifying them, and sends ONLY the 40-feature M2 allow-list
      (payload built from src.preprocessing.FEATURE_COLUMNS — never a
      hand-typed field list) to POST /predict over HTTP
- [x] label / difficulty / category / is_attack NEVER appear in any request;
      the simulator never imports the model, joblib, or sklearn, never
      touches models/, and computes NO evaluation metric of any kind —
      KDDTest+ is replay input only; the locked once-only evaluation stays
      reserved for M8
- [x] Configurable: API URL, replay rate (flows/s), row limit, optional
      duration cap, request timeout; sequential single-request pacing (no
      concurrency, no flooding); optional seeded shuffle so the demo shows
      a mix of attack types (KDDTest+ rows are ordered)
- [x] Demo-appropriate defaults (~1-2 flows/s, bounded rows), clear
      terminal progress (sent / ok / attacks observed / failures / rate)
- [x] Robust failure behavior: request timeout handled; API-down →
      wait-and-retry without losing the row; 422 and 5xx counted and
      reported, replay continues; Ctrl+C → clean summary exit

END-TO-END DEMO (all three real components)
- [x] simulator → /predict → Random Forest pipeline → API state →
      /stats + /predictions/recent → dashboard, verified live: counters
      advance, attack types accumulate, timeline/feed/alerts update, alert
      detail shows the 40 features + uncalibrated-confidence caveat, no
      ground-truth label visible anywhere in the UI
- [x] API stays responsive during replay; bounded history stays ≤ 1,000;
      dashboard keeps polling with no console errors

VERIFICATION
- [x] pytest suite for the simulator: exact payload fields, forbidden-field
      exclusion, request construction, rate pacing, row limit, timeout/422/
      5xx/connection-failure handling, clean shutdown, source scan (no
      model/evaluation references), all with mocked HTTP — no live API
      needed for unit tests
- [x] Full M1-M6 regression suite still green; adversarial audit passed

DOCS
- [x] README (demo run instructions + status), PROJECT_KNOWLEDGE, risk
      register (R9 demo rehearsal) updated

## Milestone 8 — final locked evaluation + documentation + viva prep (FINAL)

READINESS (verified by execution before the locked evaluation)
- [ ] Full M1-M7 suite green; working tree clean; KDDTest+ integrity
      re-verified (22,544 rows); production artifact reproduces its stored
      M4 validation metrics exactly on reload (unmodified-artifact proof
      that touches no test data); docs consistent; no blockers

LOCKED EVALUATION — the once-only KDDTest+ read for scoring
- [ ] Runner lives in scripts/ (OUTSIDE the guarded src/training,
      src/evaluation, src/preprocessing and api/ packages, whose
      KDDTest+-isolation scans stay in force unchanged)
- [ ] Loads the SERIALIZED pipeline only — no fit(), no tuning, no
      selection, no preprocessing changes; predicts all 22,544 rows once;
      metrics computed with the existing evaluate_predictions
- [ ] Recorded: accuracy, 5x5 confusion matrix, per-class P/R/F1,
      macro/weighted F1, binary IDS view (missed attacks / false alarms),
      throughput; results saved to models/final_test_metrics.json and
      docs/m8-final-evaluation.md and treated as LOCKED — the model is not
      changed in response, and no second scoring read happens
- [ ] Validation-vs-test comparison written honestly: effect of the 17
      test-only attack types, R2L/U2R imbalance, poor numbers NOT hidden

FINAL AUDITS
- [ ] Leakage/isolation audit re-run: forbidden columns excluded by
      construction (tests), KDDTest+ unreadable by guarded packages
      (source-scan tests), API/simulator/dashboard carry no ground truth
      (tests + UI scan), unknown categoricals safe, 422 validation intact,
      uncalibrated-confidence wording present, replay-only simulator, no
      IPS/blocking anywhere
- [ ] Performance re-measured (not quoted): model load, single-flow
      latency, real-HTTP API latency (NFR1 < 200 ms), simulator throughput
- [ ] Final adversarial review (claims vs code, terminology, hidden
      test-set usage, reproducibility) with findings resolved

DOCS + VIVA + DEMO
- [ ] docs/m8-final-evaluation.md: executive summary, architecture, frozen
      model, protocol, validation + final results, comparison,
      minority-class analysis, leakage verification, performance, known
      limitations, conclusion, reproduction/demo instructions, dataset
      citation
- [ ] docs/viva-preparation.md: the 42 agreed questions answered
      (simple-first, then technical)
- [ ] README, PROJECT_KNOWLEDGE, risk register brought to final state
- [ ] Full end-to-end demo rehearsed against the real stack and verified in
      a browser (counters, alerts, details, caveat, failure banner, no
      ground truth, no console errors)
- [ ] Full suite green at close; working tree clean; every M8 commit
      logical and explained
