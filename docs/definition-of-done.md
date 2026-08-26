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

- [ ] Majority-class baseline computed on the validation split: accuracy,
      meaningful per-class metrics, confusion matrix — the reference floor
- [ ] LogisticRegression pipeline = `build_preprocessor(scaling="standard")` +
      classifier, `RANDOM_STATE`, sensible default config, trained on the
      100,778-row training split ONLY
- [ ] RandomForest pipeline = `build_preprocessor(scaling="none")` + classifier,
      `RANDOM_STATE`, sensible default config, same training split
- [ ] All evaluation on the 25,195-row validation split ONLY: confusion matrix,
      accuracy, per-class precision/recall/F1, macro + weighted averages,
      training/prediction times
- [ ] Comparison table (baseline + both models) and a documented selection
      decision based on validation performance and IDS priorities (attack recall
      weighed against false positives) — never accuracy alone, never KDDTest+
- [ ] Selected pipeline serialized with joblib as ONE artifact (preprocessing +
      classifier) in models/, with a metadata file (model type, date, versions,
      configuration, validation metrics)
- [ ] Reload verified: artifact loads, predicts on validation samples, output is
      binary, predictions identical to pre-save
- [ ] pytest tests: pipeline construction, training + prediction, binary output
      domain, no invalid outputs, save/reload consistency, KDDTest+ source-scan
      isolation for src/training + src/evaluation
- [ ] Leakage audit passed and reproducibility demonstrated: two runs →
      identical metrics
- [ ] Docs updated: M3 results doc, README status, PROJECT_KNOWLEDGE, risk
      register review; NFR1 timing recorded
