# Milestone 8 — Final Locked Evaluation & Project Conclusion (2026-08-27)

## 1. Executive summary

An ML-based misuse-detection IDS was built end-to-end: NSL-KDD → leakage-safe
preprocessing inside one serialized sklearn Pipeline → Random Forest
multi-class classifier → FastAPI prediction service → React dashboard, with a
replay simulator driving the live demo. On its **validation split** (attack
types it was trained on) the model detects 99.78% of attacks with 5 false
alarms in 25,195 flows. On the **locked KDDTest+ benchmark** — deliberately
constructed with 17 attack types absent from training — accuracy falls to
**74.5%** and binary attack recall to **59.1%**. That drop is not a defect of
the implementation; it is the measured, honestly-reported boundary of misuse
detection: **the model detects what it has learned (76.1% of known-type
attack rows) and largely misses what it has never seen (18.0% of test-only
attack rows)**. All engineering guarantees held: zero leakage (test-enforced),
one artifact serving train-identical preprocessing, 33 ms median real-HTTP
prediction latency (NFR1 < 200 ms), and a fully rehearsed live demo.

## 2. Final architecture

```
OFFLINE  NSL-KDD (KDDTrain+) → src/preprocessing (inside the Pipeline)
         → src/training (M3 binary baseline · M4 multi-class selection)
         → models/multiclass_pipeline.joblib  (ONE artifact: preprocessing + RF)
ONLINE   simulator/ (replays KDDTest+ rows, labels stripped)
         → POST /predict (FastAPI, Pydantic validation, ADR-012)
         → frozen pipeline → bounded in-memory state
         → GET /stats + /predictions/recent (2 s polling, ADR-007)
         → React + Vite + Recharts dashboard (localhost:5173)
```

## 3. Frozen model

RandomForestClassifier, 100 trees, sklearn defaults, `RANDOM_STATE=42`,
selected at M4 over LogisticRegression and HistGradientBoosting on a
documented framework (macro F1 → minority recall → detection quality → false
positives → overall → efficiency). Serialized 2026-08-26 as
`models/multiclass_pipeline.joblib` (11.9 MB) + metadata. Before the final
evaluation, the reloaded artifact reproduced its stored validation metrics
exactly (accuracy match < 1e-12) — the artifact was provably unmodified.
It was **never** fit, tuned, or altered after M4; nothing in this milestone
changed it.

## 4. Dataset and evaluation protocol

NSL-KDD (Tavallaee et al., 2009): KDDTrain+ 125,973 rows; KDDTest+ 22,544
rows; 41 features + label + difficulty. Protocol (binding since M1, enforced
by source-scan tests): all selection/tuning on a stratified 80/20 split of
KDDTrain+ (100,778 / 25,195, stratified on the 5-way category); **KDDTest+
read for scoring exactly once**, on 2026-08-27, after every decision was
locked, by `python -m scripts.run_final_evaluation` — a script deliberately
outside the guarded packages. The demo simulator also *replays* KDDTest+
rows through the API (labels stripped, no metrics computed); replay is not
evaluation and computes nothing.

## 5. Validation results (M4, for context)

Accuracy 0.9988 · macro F1 0.9500 · R2L recall 0.9598 · U2R recall 0.70 ·
26 missed attacks / 5 false alarms in 25,195 flows. Full detail:
docs/m4-multiclass-evaluation.md.

## 6. Final KDDTest+ results (LOCKED, 22,544 rows evaluated)

| Metric | Value |
|---|---|
| Accuracy | **0.7446** |
| Macro F1 | **0.4848** |
| Weighted F1 | 0.7003 |
| Binary attack recall (ADR-012 view) | **0.5913** (5,245 of 12,833 attacks missed) |
| False alarms | 251 of 9,711 normal rows (2.6%) |
| Binary accuracy | 0.7562 |
| Predict time | 0.35 s for all 22,544 rows (0.016 ms/flow) |

## 7. Confusion matrix (rows = truth, columns = prediction)

|  | normal | dos | probe | r2l | u2r |
|---|---|---|---|---|---|
| **normal** (9,711) | 9,460 | 67 | 183 | 0 | 1 |
| **dos** (7,458) | 1,604 | 5,767 | 87 | 0 | 0 |
| **probe** (2,421) | 773 | 166 | 1,482 | 0 | 0 |
| **r2l** (2,754) | 2,675 | 0 | 2 | 75 | 2 |
| **u2r** (200) | 193 | 0 | 1 | 3 | 3 |

## 8. Per-class metrics

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| normal | 0.6433 | 0.9742 | 0.7749 | 9,711 |
| dos | 0.9612 | 0.7733 | 0.8570 | 7,458 |
| probe | 0.8444 | 0.6121 | 0.7098 | 2,421 |
| r2l | 0.9615 | **0.0272** | 0.0530 | 2,754 |
| u2r | 0.5000 | **0.0150** | 0.0291 | 200 |

Note the shape of the failure: when the model DOES flag r2l it is almost
always right (precision 0.96) — it just almost never fires. Errors flow
overwhelmingly into "normal", the signature failure mode of misuse detection.

## 9. Validation vs test comparison

| Metric | Validation | KDDTest+ | Why it moved |
|---|---|---|---|
| Accuracy | 0.9988 | 0.7446 | 17 unseen attack types + distribution shift |
| Macro F1 | 0.9500 | 0.4848 | r2l/u2r collapse drags the unweighted mean |
| Binary attack recall | 0.9978 | 0.5913 | unseen attacks predicted "normal" |
| False alarms | 5 / 13,469 | 251 / 9,711 | test normal traffic also shifts |
| R2L recall | 0.9598 | 0.0272 | see §10 |
| U2R recall | 0.70 | 0.0150 | httptunnel (133 of 200 rows) unseen |

These numbers were never expected to match: validation measures performance
on the *known-attack distribution*; KDDTest+ was designed by its authors as
a generalization stress test. Diagnostic decomposition of the locked
predictions (deterministic re-prediction, verified byte-identical to the
locked confusion matrix): **training-known attack rows: 9,083, of which
76.1% were detected as attacks; test-only attack rows: 3,750, of which
18.0% were detected** (those detections happen when a novel attack resembles
a learned one — e.g. `saint` scans were caught 98% because they resemble
`satan`, while `snmpguess`/`snmpgetattack`/`mailbomb` were missed 100%).

**Does the model still satisfy the project's objectives?** Yes, as scoped:
the objective (requirements.md) was a working, honest, explainable ML-IDS
with a live demo — not state-of-the-art benchmark scores. Detection of known
attacks is near-perfect, the false-alarm rate stays low (2.6%), and the
failure boundary is measured and explained rather than hidden. As a *real*
security control it would need to be paired with anomaly detection — stated
as a limitation, and the correct viva answer to "so is this a good IDS?"

## 10. Minority-class analysis

R2L's collapse is **two** effects, not one:
- Unseen R2L types (555 rows: snmpgetattack 178, snmpguess 331, worm, etc.):
  0.5% detected — the model has no rule for what it never saw.
- **Training-known R2L types also collapsed** (2,199 rows, only 3.5%
  detected): test R2L is dominated by `guess_passwd` (1,231 rows vs **42**
  training rows) and `warezmaster` (944 vs **15** training rows). With so
  few training examples, the learned picture of those types does not cover
  how they appear in the test set. This is minority-class starvation
  *within* known types — a subtler and more honest finding than "unseen
  types only".

U2R (200 rows): 133 are `httptunnel` (unseen; 132 missed), the rest split
across types with 3-22 training rows. 3 caught in total. Risk R7 (accepted
at Phase 0) predicted exactly this.

## 11. Leakage / isolation verification (all enforced by the 91-test suite)

- `label`, `difficulty`, `is_attack`, `category` excluded from features by
  allow-list construction (tested for both tasks).
- src/preprocessing, src/training, src/evaluation and api/ **cannot** read
  KDDTest+ — source-scan tests, all still green after M8 (the final
  evaluation runner lives in scripts/, outside all guarded packages).
- Preprocessing fitted on the training split only, inside the Pipeline.
- Simulator payloads carry exactly the 40 features (tested); the rendered
  dashboard exposes no ground-truth field (browser-verified).
- The API never sees ground truth; `/predict` serves the frozen multi-class
  artifact only (ADR-012, test-enforced).
- Model selection, tuning and preprocessing decisions all predate the single
  KDDTest+ read; nothing was changed after it.

## 12. Performance measurements (measured 2026-08-27, this machine)

| What | Measured |
|---|---|
| Model load (cold) | 0.29 s |
| Batch prediction | 0.016 ms/flow (22,544 rows in 0.35 s) |
| API real-HTTP warm latency | **median 33 ms, p95 40 ms, max 44 ms** (NFR1 < 200 ms ✓) |
| Simulator throughput | 4.04 flows/s at a 4.0 target (paced, single-request) |
| Dashboard | 2 s polling; counters/charts update live (browser-verified) |

## 13. Known limitations (stated, not hidden)

1. 1998-era dataset; several content features assume plaintext, host-audited
   traffic — unavailable to a modern network-only IDS.
2. Misuse detection cannot flag novel attacks (measured above: 18% on
   unseen types); a production system would pair it with anomaly detection.
3. U2R/R2L results rest on extreme imbalance (42 U2R training rows) and, for
   R2L, on known types with 15-42 training examples.
4. `confidence` is an uncalibrated vote fraction, labeled as such everywhere.
5. Demo traffic is a replay (~57% attacks — a benchmark artifact, not a real
   base rate); it is "simulated traffic replay through the same prediction
   API path", never "live network detection".
6. Detection only — no prevention/blocking. Localhost only. In-memory
   history resets on API restart (by design).

## 14. Final conclusion

The project delivers what it froze at Phase 0: a reproducible, leakage-clean,
fully tested (91 backend + 14 frontend tests), documented ML-IDS with a live
end-to-end demo and honest final numbers. The validation-vs-test gap is the
central *finding*, not an embarrassment: it quantifies the known-attack
boundary of supervised misuse detection on the benchmark designed to expose
exactly that.

## 15. Reproduction / demo instructions

README.md steps 1-8 reproduce everything from a fresh clone: venv + pinned
deps → dataset download (integrity-checked) → 91 tests → artifact build →
API (:8000) → dashboard (:5173) → simulator replay. Every stochastic step
uses `RANDOM_STATE=42`; two independent M4 runs were byte-identical. The
final evaluation is reproduced by `python -m scripts.run_final_evaluation`
(the script refuses to run while `models/final_test_metrics.json` exists —
the lock is mechanical, not just procedural).

## 16. Dataset citation

M. Tavallaee, E. Bagheri, W. Lu, A. A. Ghorbani, "A Detailed Analysis of the
KDD CUP 99 Data Set," *IEEE Symposium on Computational Intelligence for
Security and Defense Applications (CISDA)*, 2009. NSL-KDD distribution:
University of New Brunswick, Canadian Institute for Cybersecurity.
