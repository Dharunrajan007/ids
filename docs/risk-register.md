# Risk Register (living document — statuses reviewed every milestone)

Last reviewed: 2026-08-26 (Milestone 3)

| ID | Risk | Probability | Impact | Mitigation | Status |
|----|------|-------------|--------|------------|--------|
| R1 | Misleading accuracy: imbalanced classes + unseen attack types in KDDTest+ make "99% accuracy" claims false | High | High | evaluate_predictions always emits confusion matrix + per-class recall/F1; M3 doc reports FN/FP counts explicitly and labels all numbers validation-only | Actively mitigated (final honesty check at M8 report) |
| R2 | Train/serve feature mismatch: API feeds the model differently-shaped data than training | Medium | High | Single serialized sklearn Pipeline used in both places (ADR-005) | Mitigated by design |
| R3 | Data leakage: fitting scalers/encoders on test data inflates results | Medium | High | Fit transformers on training split only; binding evaluation protocol below; enforced by M2 automated tests (feature allow-list, transform-without-refit, source-scan proving src/preprocessing cannot read KDDTest+) | Mitigated by design + tests |
| R4 | Model overfitting to training data | Medium | High | Stratified validation split per the evaluation protocol below; train-vs-validation gap checked each model (M3: LogReg no gap; RF 1.0000 train vs 0.9988 validation — 0.12 pp, not harmful in-distribution); true generalization check = the single KDDTest+ evaluation | Open (monitored) |
| R5 | React integration friction (frontend tooling eats sessions) | Medium | Medium | API built and tested first (M5 before M6); minimal component set; Recharts | Open |
| R6 | Dataset corruption / accidental modification of raw files | Low | High | Raw data is read-only by convention: scripts never write to data/raw/; re-downloadable via src/download_data.py | Mitigated by design |
| R7 | Rare classes (U2R ~50 training samples) perform badly | High | Medium | Acknowledge honestly in evaluation; explain in viva rather than hide | Accepted |
| R8 | Scope creep (packet capture, deep learning, "real" blocking) | Medium | Medium | Frozen out-of-scope list in requirements.md; changes need a new ADR | Mitigated by design |
| R9 | Demo-day failure (dependency/env breakage on presentation machine) | Low | High | README-only setup (NFR3); full rehearsal in Milestone 7; no internet needed during demo (NFR2) | Open |
| R10 | Single-copy repository: no git remote, whole project lives on one laptop | Medium | High | Push to a private GitHub remote + tag milestones (Milestone-1 review must-fix; pending user action) | Open |

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
