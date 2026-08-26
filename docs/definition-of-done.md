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
