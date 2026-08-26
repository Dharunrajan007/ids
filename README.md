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
│   ├── training/          (Milestones 3-4)
│   └── evaluation/        (Milestones 3-4)
├── tests/         automated verification (pytest — see step 4 below)
├── models/        saved model artifacts (gitignored)
├── api/           FastAPI prediction service (Milestone 5)
├── simulator/     traffic replay script (Milestone 7)
├── dashboard/     React app (Milestone 6)
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
```

## Documentation

| Document | Purpose |
|---|---|
| [docs/requirements.md](docs/requirements.md) | Frozen Phase 0: requirements, scope, success criteria |
| [docs/api-contract.md](docs/api-contract.md) | API interface, frozen before backend code |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture Decision Records (the "why" behind every choice) |
| [docs/risk-register.md](docs/risk-register.md) | Living risk table, updated each milestone |
| [docs/definition-of-done.md](docs/definition-of-done.md) | Completion checklist per milestone |
| [docs/data-dictionary.md](docs/data-dictionary.md) | Every dataset column explained |

## Project status

- [x] Phase 0 — requirements & engineering foundation (frozen 2026-07-28)
- [x] Milestone 1 — setup, dataset download, exploration
- [x] Milestone 1 closeout — review must-fixes: ADR-012, src package, pinned
      deps, seed + evaluation protocol, M2 preprocessing decisions (2026-08-26)
- [x] Milestone 2 — preprocessing pipeline: leakage-safe feature/target
      separation, encoding, scaling variants, stratified validation split,
      pytest suite (2026-08-26)
- [ ] Milestone 3 — binary baseline model + evaluation
- [ ] Milestone 4 — attack-type classification + model comparison
- [ ] Milestone 5 — prediction API
- [ ] Milestone 6 — React dashboard
- [ ] Milestone 7 — traffic simulator + end-to-end demo
- [ ] Milestone 8 — final documentation
