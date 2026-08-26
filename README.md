# AI-Powered Intrusion Detection System (IDS)

A college project that classifies network traffic flows as **normal** or **attack**
(and identifies the attack category) using machine learning on the NSL-KDD dataset.

## How it works

```
OFFLINE:  NSL-KDD dataset → preprocessing → model training → saved pipeline (.joblib)
ONLINE:   traffic simulator → FastAPI /predict → React dashboard (alerts + charts)
```

The simulator replays real test-set flows to the API so the dashboard behaves like
a live IDS without needing packet capture.

## Project structure

```
ids/
├── data/          raw + processed NSL-KDD (gitignored — see setup below)
├── notebooks/     exploration only; production logic lives in src/
├── src/
│   ├── config.py          paths, column names, attack category mapping, RANDOM_STATE
│   ├── data_loader.py     loads NSL-KDD with proper column names
│   ├── preprocessing/     feature/target separation, encoding, scaling,
│   │                      stratified train/validation split (Milestone 2)
│   ├── training/          binary.py + runner (M3); multiclass.py + runner (M4)
│   └── evaluation/        metrics.py — confusion matrix + per-class P/R/F1
├── tests/         automated verification (pytest — see step 4 below)
├── models/        saved model artifacts (gitignored)
├── api/           FastAPI prediction service (Milestone 5)
├── simulator/     traffic replay script (Milestone 7)
├── dashboard/     React + Vite + Recharts dashboard (Milestone 6 — see step 7)
└── docs/          requirements, API contract, decisions (ADRs), risk register,
                   definition of done, data dictionary
```

## Setup

Requires **Python 3.14** (requirements.txt is pinned against 3.14.0).
Run all commands from the project root — `src/` is a package, so scripts are
executed with `python -m`.

```powershell
# 1. Create environment and install dependencies
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Download the NSL-KDD dataset into data/raw/
.\.venv\Scripts\python.exe -m src.download_data

# 3. Verify everything loads
.\.venv\Scripts\python.exe -m src.data_loader

# 4. Run the automated tests
.\.venv\Scripts\python.exe -m pytest

# 5. Build the production model artifact (M4 pipeline, ~30 s)
.\.venv\Scripts\python.exe -m src.training.train_multiclass --save random_forest

# 6. Start the prediction API  →  http://localhost:8000/docs
.\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000

# 7. Start the dashboard (needs Node.js; run in a second terminal)
cd dashboard; npm install; npm run dev   # → http://localhost:5173

# 8. Replay simulated traffic through the API (third terminal; Ctrl+C to stop)
.\.venv\Scripts\python.exe -m simulator.run          # 300 flows @ 1.5/s
```

The API loads `models/multiclass_pipeline.joblib` once at startup and serves
the four contract endpoints (`/predict`, `/stats`, `/predictions/recent`,
`/health`). Prediction history is in-memory and bounded; it resets on restart
by design. The `confidence` field is the model's maximum class probability and
is **uncalibrated** — a relative score, not a correctness guarantee.

## Documentation

| Document | Purpose |
|---|---|
| [docs/requirements.md](docs/requirements.md) | Frozen Phase 0: requirements, scope, success criteria |
| [docs/api-contract.md](docs/api-contract.md) | API interface, frozen before backend code |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture Decision Records (the "why" behind every choice) |
| [docs/risk-register.md](docs/risk-register.md) | Living risk table, updated each milestone |
| [docs/definition-of-done.md](docs/definition-of-done.md) | Completion checklist per milestone |
| [docs/data-dictionary.md](docs/data-dictionary.md) | Every dataset column explained |
| [docs/preprocessing-decisions.md](docs/preprocessing-decisions.md) | Approved M2 preprocessing decisions |
| [docs/m3-binary-evaluation.md](docs/m3-binary-evaluation.md) | M3 binary model results and selection |
| [docs/m4-multiclass-evaluation.md](docs/m4-multiclass-evaluation.md) | M4 multi-class results, minority-class analysis, selection |
| [docs/m8-final-evaluation.md](docs/m8-final-evaluation.md) | FINAL locked KDDTest+ results, comparison, conclusion |
| [docs/viva-preparation.md](docs/viva-preparation.md) | Viva Q&A (42 questions, simple-first answers) |

## Project status

- [x] Phase 0 — requirements & engineering foundation (frozen 2026-07-28)
- [x] Milestone 1 — setup, dataset download, exploration
- [x] Milestone 1 closeout — review must-fixes: ADR-012, src package, pinned
      deps, seed + evaluation protocol, M2 preprocessing decisions (2026-08-26)
- [x] Milestone 2 — preprocessing pipeline: leakage-safe feature/target
      separation, encoding, scaling variants, stratified validation split,
      pytest suite (2026-08-26)
- [x] Milestone 3 — binary baseline model: majority baseline vs LogReg vs
      Random Forest on the stratified validation split; RF selected (attack
      recall 0.9978, 5 false positives) and serialized with its preprocessing
      as one pipeline; KDDTest+ untouched (2026-08-26)
- [x] Milestone 4 — multi-class model (normal/DoS/Probe/R2L/U2R): majority
      baseline vs LogReg vs Random Forest vs HistGradientBoosting; RF selected
      (macro F1 0.9500, U2R recall 0.70, 26 missed attacks / 5 false alarms)
      and serialized as the production candidate pipeline (ADR-012);
      KDDTest+ still untouched (2026-08-26)
- [x] Milestone 5 — prediction API: FastAPI service over the serialized M4
      pipeline (ADR-012); 40-feature validated schema, bounded in-memory
      stats/history, CORS for the Vite dev origin; warm prediction latency
      15 ms median over real HTTP (NFR1 < 200 ms); 30 API tests (2026-08-26)
- [x] Milestone 6 — React dashboard: Vite + Recharts SOC-style UI polling the
      API every 2 s (ADR-007) — live feed, attack alerts, counters, per-minute
      timeline, category breakdown, clickable detail panel with the
      uncalibrated-confidence caveat; disconnect/empty states handled;
      14 vitest unit tests + 15 live headless-browser integration checks
      against the real API (2026-08-26)
- [x] Milestone 7 — traffic simulator + end-to-end demo: simulator/ replays
      KDDTest+ rows through POST /predict (simulated traffic replay via the
      same prediction API path — not live capture, not evaluation; labels
      never leave the process); configurable rate/rows/duration, paced
      single-request sending, clean failure/Ctrl+C handling; 13 mocked-HTTP
      tests; full simulator→API→dashboard demo verified live in a headless
      browser (2026-08-27)
- [x] Milestone 8 — FINAL: locked KDDTest+ evaluation (exactly once,
      2026-08-27) — accuracy 0.7446, macro F1 0.4848, binary attack recall
      0.5913 vs 0.9978 on validation; the honest generalization boundary of
      misuse detection, analyzed in docs/m8-final-evaluation.md; final
      leakage audit, measured performance (API 33 ms median), viva prep,
      demo rehearsed. PROJECT COMPLETE (2026-08-27)
