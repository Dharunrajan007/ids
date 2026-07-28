# Risk Register (living document — statuses reviewed every milestone)

Last reviewed: 2026-07-28 (Milestone 1)

| ID | Risk | Probability | Impact | Mitigation | Status |
|----|------|-------------|--------|------------|--------|
| R1 | Misleading accuracy: imbalanced classes + unseen attack types in KDDTest+ make "99% accuracy" claims false | High | High | Evaluate with confusion matrix, per-class recall, F1 from Milestone 3 onward; never report accuracy alone | Open |
| R2 | Train/serve feature mismatch: API feeds the model differently-shaped data than training | Medium | High | Single serialized sklearn Pipeline used in both places (ADR-005) | Mitigated by design |
| R3 | Data leakage: fitting scalers/encoders on test data inflates results | Medium | High | Fit transformers on training split only; explicit check in Milestone 2 review | Open |
| R4 | Model overfitting to training data | Medium | High | Validation split + cross-validation in Milestones 3-4; compare train vs test metrics | Open |
| R5 | React integration friction (frontend tooling eats sessions) | Medium | Medium | API built and tested first (M5 before M6); minimal component set; Recharts | Open |
| R6 | Dataset corruption / accidental modification of raw files | Low | High | Raw data is read-only by convention: scripts never write to data/raw/; re-downloadable via src/download_data.py | Mitigated by design |
| R7 | Rare classes (U2R ~50 training samples) perform badly | High | Medium | Acknowledge honestly in evaluation; explain in viva rather than hide | Accepted |
| R8 | Scope creep (packet capture, deep learning, "real" blocking) | Medium | Medium | Frozen out-of-scope list in requirements.md; changes need a new ADR | Mitigated by design |
| R9 | Demo-day failure (dependency/env breakage on presentation machine) | Low | High | README-only setup (NFR3); full rehearsal in Milestone 7; no internet needed during demo (NFR2) | Open |
