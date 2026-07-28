# Architecture Decision Records

Format: Decision / Reason / Alternatives / Consequences.
Newest entries at the bottom. Frozen decisions are never edited — superseding
a decision means writing a new ADR that references the old one.

---

## ADR-001 — Use NSL-KDD as the primary dataset

**Decision:** NSL-KDD (KDDTrain+ / KDDTest+) is the project dataset.
**Reason:** Small (~148k rows), clean labels, official train/test split with
deliberately unseen attack types (credible evaluation story), 4 well-defined attack
categories, loads and trains in minutes on a laptop.
**Alternatives:** CICIDS2017 — more modern/realistic but ~2.8M rows, known label noise,
NaN/Infinity values, and heavy cleaning effort before any model exists.
**Consequences:** Less realistic (1998-era traffic); mitigated by a dataset-agnostic
pipeline and optional Milestone 9 (CICIDS2017 comparison).

## ADR-002 — scikit-learn for ML

**Decision:** Classical ML with scikit-learn.
**Reason:** Tabular flow data is classical-ML territory; tree ensembles match or beat
neural nets on tabular data, train on CPU in minutes, and are explainable in a viva.
**Alternatives:** PyTorch/TensorFlow — complexity without benefit at this scale.
**Consequences:** No deep-learning talking point; acceptable per scope.

## ADR-003 — FastAPI for the prediction API

**Decision:** FastAPI + Uvicorn.
**Reason:** Pydantic input validation satisfies NFR6 for free; auto-generated
interactive docs at /docs are demo-friendly.
**Alternatives:** Flask (equally simple, no built-in validation), Django (oversized —
we need 3 endpoints, not an ORM/admin).
**Consequences:** One more concept to learn (Pydantic models); worth it.

## ADR-004 — React (Vite) + Recharts for the dashboard

**Decision:** React with Vite tooling; Recharts for charts.
**Reason:** Demonstrating real frontend skills is a stated project objective;
Recharts is declarative and React-native with a small learning curve.
**Alternatives:** Streamlit (faster to build but doesn't demonstrate frontend skills),
plain HTML/JS (harder to keep maintainable), D3 (a course in itself).
**Consequences:** ~1 extra session of work versus Streamlit; accepted trade-off.

## ADR-005 — Single serialized scikit-learn Pipeline for train/serve parity

**Decision:** All preprocessing lives inside one sklearn Pipeline, serialized together
with the model; the API loads and uses that exact object.
**Reason:** Eliminates the #1 student-ML bug: training-time and prediction-time
preprocessing drifting apart (NFR5).
**Alternatives:** Separate preprocessing code in API — rejected as the main bug source.
**Consequences:** Preprocessing must be expressed as sklearn transformers.

## ADR-006 — Simulator replays test flows; no live packet capture

**Decision:** A script replays KDDTest+ rows to the API at a configurable rate.
**Reason:** Live capture requires drivers, admin rights, and a feature extractor —
weeks of work orthogonal to the ML objectives. Replay gives a live-feeling demo safely.
**Alternatives:** Scapy/pyshark live capture — out of scope.
**Consequences:** Demo traffic is replayed, not real; stated honestly in the report.

## ADR-007 — Dashboard polls the API (no WebSockets)

**Decision:** Dashboard polls /stats and /predictions/recent every 2 s.
**Reason:** Indistinguishable from push in a demo; trivial to debug.
**Alternatives:** WebSockets — connection-lifecycle complexity for no visible gain.
**Consequences:** Up to 2 s display latency; irrelevant at demo scale.

## ADR-008 — Bounded in-memory prediction history; no database

**Decision:** API keeps recent predictions in a bounded in-memory list.
**Reason:** Project constraint (no databases); a demo doesn't need durable history.
**Alternatives:** SQLite — durable but adds schema/IO code for no demo value.
**Consequences:** History resets on API restart; acceptable.

## ADR-009 — joblib for model serialization

**Decision:** Save the Pipeline with joblib.
**Reason:** scikit-learn standard; efficient with numpy arrays.
**Alternatives:** pickle (less efficient), ONNX (cross-platform deployment we don't need).
**Consequences:** Model files only loadable from Python; fine — the API is Python.

## ADR-010 — Phase 0 is frozen

**Decision:** requirements.md and api-contract.md are frozen as of 2026-07-28.
**Reason:** Prevent endless redesign before code exists; mirror real change management.
**Alternatives:** Living requirements doc — rejected (invites silent drift).
**Consequences:** Any change after this date is a new ADR, giving a traceable history.

## ADR-011 — Notebook-style exploration uses `# %%` Python files

**Decision:** Exploration files are plain .py files with `# %%` cell markers
(VS Code runs them like notebooks) instead of .ipynb.
**Reason:** Diff-able in git, runnable as plain scripts, no Jupyter dependency;
the user works in VS Code where `# %%` gives the same interactive experience.
**Alternatives:** .ipynb — richer output storage but noisy diffs and extra dependency.
**Consequences:** Cell outputs aren't stored in the file; findings that matter are
written into docs/ instead (which we want anyway).
