# Viva Preparation (2026-08-27)

Format per answer: plain-language first, then the technical detail worth
adding. Numbers come from the locked results (docs/m8-final-evaluation.md).

**1. What is an IDS?** A system that watches traffic and raises an alert
when something looks like an attack — a burglar alarm for a network.
Technically: ours classifies summarized connection records (flows) as
normal/attack and names the attack category; it detects and alerts only.

**2. IDS vs IPS?** An IDS *tells* you about an attack; an IPS also *blocks*
it. Blocking needs inline placement and creates a new risk — a false
positive now cuts off legitimate traffic. This project is detection-only by
frozen scope.

**3. Why misuse detection?** We teach the model known attacks from labeled
examples — like a guard with a book of wanted posters. The trade-off is
measured in our results: 76% detection on known attack types vs 18% on
types absent from training. Anomaly detection (model normal, flag
deviations) is the complement, and deliberately out of scope.

**4. Why machine learning?** Hand-written rules for 41 interacting features
don't scale and can't generalize even slightly; a learned model finds the
patterns itself and gives per-class probabilities. The cost: it needs
labeled data and inherits that data's blind spots.

**5. Why NSL-KDD?** The standard teaching/benchmark IDS dataset: cleaned of
KDD'99's duplicates, small enough to iterate on a laptop, with a deliberate
train/test design (17 test-only attack types) that forces an honest
generalization discussion. Its age (1998 traffic) is a stated limitation.

**6. What is a network flow?** One summarized connection — "who talked to
whom, over what service, how many bytes, with what error pattern" — not
individual packets. Each NSL-KDD row is one flow with 41 precomputed
features.

**7. The 40 model features?** The 41 dataset features minus
`num_outbound_cmds` (constant zero — no information). Grouped as in Q8; the
exact allow-list lives in one place (`src.preprocessing.FEATURE_COLUMNS`)
and the API schema is generated from it.

**8. The four feature groups?** (1) Basic connection facts from headers
(duration, protocol, service, bytes); (2) content features from payloads
(failed logins, root shell — possible only because DARPA traffic was
plaintext); (3) time-based traffic stats over the last 2 seconds (counts,
error rates); (4) host-based traffic stats over the last 100 connections to
the same destination.

**9. Why is `difficulty` removed?** It records how many of the dataset
authors' own classifiers got that row right — it encodes evaluation
information about the answer. Using it is leakage; it is excluded by
construction and a test proves it can never reach the feature matrix.

**10. What is data leakage?** Information from the answer, or from data you
are supposed to be tested on later, sneaking into training — like revising
from the exam paper. Consequences here would be inflated scores that
collapse in reality. Our defenses: allow-list feature selection,
fit-on-train-only, and source-scan tests that make the guarded packages
*unable* to read KDDTest+.

**11. Why an allow-list?** Excluding "bad" columns fails silently when a new
column appears; *including* exactly the 40 known features means anything
unexpected — including the targets — is dropped by construction, no matter
what the input frame carries.

**12. Why OneHotEncoder?** `protocol_type`/`service`/`flag` are categories
without order. Numbering them (tcp=1, udp=2) would invent a fake ordering;
one-hot gives each value its own 0/1 column — 84 columns for the three
features, 121 model inputs total.

**13. Why `handle_unknown="ignore"`?** A category the encoder never saw
(say a new service name arriving via the API) encodes as all-zeros instead
of crashing the request. Verified live: an unknown service still returns a
prediction; NSL-KDD's own test set contains no unseen categorical values.

**14. Why repair `su_attempted`?** Its documented domain is {0,1} but 61
rows contain 2 ("attempted and succeeded" in the original collection).
Recoded 2→1 inside the pipeline as a named step: "su was attempted" is
factually true, and left alone a tree could memorize the artifact rule
`su_attempted==2 → normal`, an inexplicable quirk.

**15. Why scaling (and why per model family)?** Feature scales span 9
orders of magnitude (`src_bytes` max 1.38 billion). Logistic regression
sums weighted features, so it gets StandardScaler; trees split on
thresholds and are scale-invariant, so they keep raw, interpretable units.
MinMax was rejected: one huge outlier would squash the bulk of the feature
into ~[0, 1e-7]. The scaling travels inside the serialized pipeline, so
serving can never mismatch it.

**16. Why Logistic Regression?** The explainable linear reference: a
weighted sum of evidence per class. Its 97.4%/98.9% (binary/multi)
validation accuracy also *tells* us the task is largely linearly separable
— useful context for judging fancier models.

**17. Why Random Forest?** 100 decision trees, each trained on a random
bootstrap sample with random feature subsets, voting. Trees carve out
combinations ("this service with this error pattern"), which suits tabular
flow data with categorical structure; the ensemble averages away single-tree
overfitting.

**18. Why HistGradientBoosting?** The third candidate family — boosting
builds trees sequentially, each correcting the last. It is sklearn-native
(no XGBoost dependency) and the strongest classical tabular family, so its
inclusion makes the comparison meaningful.

**19. Why did Random Forest win?** It dominated every criterion at once:
macro F1 0.9500 (vs 0.8559 LogReg, 0.8121 HGB), best R2L/U2R recall, fewest
missed attacks (26) and false alarms (5), fastest training (4.3 s). HGB is
the instructive loser: 99.5% accuracy but U2R precision 0.10 — 35 false U2R
alarms — which macro F1 exposed and weighted metrics hid.

**20. Why macro F1?** It averages the five classes *equally*, so the
10-row U2R class counts as much as the 13,469-row normal class — minority
failure cannot hide. Weighted F1 tracked accuracy for all candidates and
would have picked the same winner for the wrong reason.

**21. Why not accuracy alone?** "Always predict normal" scores 53.5%
accuracy while catching zero of 11,726 attacks. Accuracy without per-class
recall is meaningless under imbalance — recorded as risk R1 on day one.

**22. Why is U2R difficult?** 42 training rows against 53,874 normal — a
1295:1 imbalance; the loss function barely notices the class. The final
test confirmed it: 3 of 200 U2R rows caught, 133 of which were an unseen
type (`httptunnel`).

**23. What does confidence mean?** The model's probability for the winning
class — for the forest, the fraction of trees that voted for it: 0.96 means
96 of 100 trees agreed.

**24. Why is it uncalibrated?** Tree-vote fractions are not empirical
frequencies — among predictions with "confidence 0.9", the true accuracy is
not guaranteed to be 90%. Calibration (e.g. isotonic/Platt) was out of
scope, so every surface that shows confidence carries the caveat.

**25. Why one serialized Pipeline?** Preprocessing and model travel as one
artifact, so serve-time transformation is *identical* to train-time by
construction — the classic train/serve skew bug becomes impossible
(ADR-005). Also one file to version, load, and explain.

**26. Why FastAPI?** Modern Python web framework with Pydantic validation
built in, automatic OpenAPI docs at /docs, and enough performance for this
use; the ML stack is already Python, so the model loads in-process.

**27. Why load the model once?** Loading the 12 MB artifact takes ~1 s; a
prediction takes ~10 ms. Loading per request would multiply latency ~100×
for nothing. It loads in the startup lifespan; a test proves `joblib.load`
is never called during requests.

**28. Why Pydantic?** Declarative validation: the request schema (all 40
features, typed) is checked before any code runs, with field-level errors.
Ours is *generated from* the M2 allow-list, so schema and pipeline cannot
drift apart.

**29. Why HTTP 422?** "I understood the request format, but the content is
invalid" — missing/extra/wrong-typed fields get a structured error naming
the field, never a crash (NFR6). Distinct from 400 (unreadable) and 500
(server bug).

**30. Why CORS?** Browsers block a page on :5173 from calling :8000 unless
the API explicitly allows that origin. We allow exactly the Vite dev
origins — not `*`, which would let any web page a browser visits talk to
the local IDS.

**31. Why polling instead of WebSockets?** Every 2 s the dashboard asks
"what's new?" — dead simple, stateless, debuggable with curl, and at demo
scale the cost is negligible. WebSockets add connection state and failure
modes for no demo value (ADR-007).

**32. Why no database?** The demo needs recent history, not durable
history. A bounded in-memory deque (1,000 records + 60-minute timeline +
lifetime counters) does that with zero infrastructure; history resetting on
restart is documented, intentional behavior (ADR-008).

**33. Why replay instead of packet capture?** Capture needs privileged
drivers and protocol parsing, and the model consumes *flows*, not packets —
someone would still have to compute 41 features per connection in real
time. Replaying real recorded flows exercises the identical prediction path
(ADR-006).

**34. Why does the simulator use KDDTest+?** Demo traffic should be data
the model never trained on, so predictions are genuine, and its ~57% attack
mix makes an engaging demo (a stated benchmark artifact, not a realistic
base rate).

**35. Why isn't simulator replay considered evaluation?** Evaluation
compares predictions against ground truth and lets the comparison influence
decisions. The simulator never reads a metric and never compares anything —
labels never even leave its process. Source-scan tests ban every metric
term from the simulator package.

**36. How is ground truth kept away from /predict?** Defense in depth:
payloads are built strictly from the 40-column allow-list (labels never
selected); the API schema rejects any extra field with 422; tests assert
the forbidden fields never appear; and the rendered dashboard was
browser-scanned for ground-truth fields.

**37. Why might KDDTest+ performance be lower?** It *is* lower — by design.
17 attack types appear only in the test set (18% detected), and even known
minority types shift: test R2L is dominated by `guess_passwd` (1,231 rows
vs 42 in training) and `warezmaster` (944 vs 15). Accuracy 0.9988 → 0.7446,
attack recall 0.9978 → 0.5913. Misuse detection detects what it learned.

**38. Project limitations?** 1998-era data; novel attacks largely missed
(measured); U2R/R2L starved of training examples; uncalibrated confidence;
replay-based demo with benchmark attack rates; detection-only; localhost;
in-memory history. All stated in the final report — none hidden.

**39. Unknown service/category at predict time?** The one-hot encoder emits
all-zeros for that feature block (`handle_unknown="ignore"`), the forest
still votes, the API returns a normal response. Verified by test and live.

**40. What if the API goes down?** Dashboard: red "API unreachable" banner,
keeps the last data visible, retries every 2 s, recovers automatically
(browser-verified). Simulator: retries the same row every 2 s until the API
returns — nothing lost, nothing duplicated.

**41. What happens on malformed input?** HTTP 422 with field-level detail —
missing fields, unknown fields, wrong types, NaN/Infinity, out-of-float32
range values, even a 6,000-deep nested JSON bomb (the last three were found
by adversarial audit and fixed with a sanitizing error handler). The
process never crashes; the next request works.

**42. The complete architecture, end-to-end?** Offline: KDDTrain+ is split
80/20 (stratified, seeded); preprocessing + Random Forest are fitted as one
Pipeline on the training split, selected on validation, serialized once.
Online: the simulator replays KDDTest+ rows — 40 features only — to
POST /predict; Pydantic validates; the frozen pipeline preprocesses and
votes; the API answers {prediction, attack_type, confidence, timestamp},
stores it in bounded memory, and the dashboard polls /stats +
/predictions/recent every 2 s to render counters, charts, the live feed,
alerts and the detail panel. KDDTest+ was scored exactly once, at the very
end, and the numbers were reported honestly.
