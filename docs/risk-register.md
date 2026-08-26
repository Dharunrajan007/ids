# Risk Register (living document — statuses reviewed every milestone)

Last reviewed: 2026-08-27 (Milestone 8 — FINAL; project complete)

| ID | Risk | Probability | Impact | Mitigation | Status |
|----|------|-------------|--------|------------|--------|
| R1 | Misleading accuracy: imbalanced classes + unseen attack types in KDDTest+ make "99% accuracy" claims false | High | High | evaluate_predictions always emits confusion matrix + per-class recall/F1; the M8 final report leads with the honest 0.7446/0.5913 KDDTest+ numbers next to validation, with the seen-vs-unseen decomposition | Closed (final report honest by construction) |
| R2 | Train/serve feature mismatch: API feeds the model differently-shaped data than training | Medium | High | Single serialized sklearn Pipeline used in both places (ADR-005); M5 additionally derives the API request schema from the same FEATURE_COLUMNS constant and tests API-vs-artifact prediction identity | Mitigated by design + tests |
| R3 | Data leakage: fitting scalers/encoders on test data inflates results | Medium | High | Fit transformers on training split only; binding evaluation protocol below; enforced by M2 automated tests (feature allow-list, transform-without-refit, source-scan proving src/preprocessing cannot read KDDTest+) | Mitigated by design + tests |
| R4 (closed at M8: the single locked KDDTest+ evaluation is done; gap reported honestly) | Model overfitting to training data | Medium | High | Stratified validation split per the evaluation protocol below; train-vs-validation gap checked each model (M3 and M4: LogReg no gap; RF 1.0000 train vs 0.9988 validation — 0.12 pp; HGB 0.16 pp — none harmful in-distribution); true generalization check = the single KDDTest+ evaluation | Open (monitored) |
| R5 | React integration friction (frontend tooling eats sessions) | Medium | Medium | API built and tested first; minimal component set; Recharts. M6 landed against the live API with headless-browser verification (polling cadence, disconnect recovery, responsive layout) | Closed (M6 done) |
| R6 | Dataset corruption / accidental modification of raw files | Low | High | Raw data is read-only by convention: scripts never write to data/raw/; re-downloadable via src/download_data.py | Mitigated by design |
| R7 | Rare classes (U2R ~50 training samples) perform badly | High | Medium | Acknowledged and measured to the end: final U2R recall 0.0150, R2L 0.0272 (unseen types + 15-42-row known types); full decomposition in docs/m8-final-evaluation.md §10; viva answer prepared | Accepted (materialized as predicted, honestly reported) |
| R8 | Scope creep (packet capture, deep learning, "real" blocking) | Medium | Medium | Frozen out-of-scope list in requirements.md; changes need a new ADR | Mitigated by design |
| R9 | Demo-day failure (dependency/env breakage on presentation machine) | Low | High | README-only setup (NFR3); full simulator→API→dashboard rehearsal done at M7 (320 flows, zero failures); no internet needed during demo (NFR2). Re-rehearse on the actual presentation machine before the viva | Mitigated (final rehearsal pending) |
| R10 | Single-copy repository: no git remote, whole project lives on one laptop | Medium | High | Pushed to private remote github.com/Dharunrajan007/ids with milestone-1..8 tags (2026-08-27) | Closed |

## Evaluation protocol (binding rule — recorded at Milestone-1 closeout, 2026-08-26)

```
KDDTrain+
   ↓  stratified validation split / stratified cross-validation
model selection + hyperparameter tuning   (ALL choices happen here)
   ↓  model and hyperparameters locked
KDDTest+  — used exactly ONCE, for the final reported evaluation
```

- **KDDTest+ must NEVER be used to select the winning model** or tune anything.
  It is touched once, after every choice is locked (mitigates R1, R3, R4).
- **Stratification always uses the 5-way `category` target**
  (normal / DoS / Probe / R2L / U2R), including for the binary task — otherwise
  a random split could hold out most of the 52 U2R training rows.
- Every split/CV/model seed uses `RANDOM_STATE = 42` from `src/config.py`.
- The dataset files themselves are never altered (raw data is read-only, R6).
