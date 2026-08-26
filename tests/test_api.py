"""Milestone-5 verification: the FastAPI prediction service.

Runs the real application (lifespan included) against the real serialized M4
artifact through FastAPI's in-process TestClient — no network, same code path.
Skips as a module if the artifact hasn't been built on this machine (it is
gitignored; regenerate with `python -m src.training.train_multiclass --save
random_forest`).

Real KDDTrain+ validation rows are used ONLY to exercise the request path.
No model performance is computed or reported here — that is M4's job, and
KDDTest+ stays untouched as always.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import joblib
import pytest
from fastapi.testclient import TestClient

import api as api_pkg
from api.model_service import MODEL_FILE
from api.state import HISTORY_LIMIT, PredictionHistory
from src.preprocessing import split_features_target

# The artifact is gitignored, so endpoint tests skip on a machine that hasn't
# built it yet — but ONLY via this fixture: the source-scan tests below run
# unconditionally (audit finding: a module-level skip would silently disable
# the ADR-012 and KDDTest+ isolation guards on a fresh clone).
needs_artifact = pytest.mark.skipif(
    not MODEL_FILE.exists(),
    reason="multiclass_pipeline.joblib not built on this machine",
)

# --- Fixtures -------------------------------------------------------------


@pytest.fixture(scope="session")
def client():
    if not MODEL_FILE.exists():
        pytest.skip("multiclass_pipeline.joblib not built on this machine")
    from api.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def fresh_history(client):
    """Each test starts from empty in-memory state, exactly like a restart."""
    client.app.state.history.reset()


@pytest.fixture(scope="session")
def validation_features(split_frames):
    """(features_dict, true_category) pairs from the validation split."""
    _, val_df = split_frames
    X, y = split_features_target(val_df, "multiclass")
    return X, y


@pytest.fixture(scope="session")
def one_row(validation_features):
    X, _ = validation_features
    return X.iloc[0].to_dict()


@pytest.fixture(scope="session")
def row_predicted_as(validation_features, client):
    """Find a validation row the SERVED pipeline deterministically assigns to
    a given category (searching truth-labeled rows of that category first)."""
    X, y = validation_features
    pipeline = client.app.state.model_service.pipeline

    def find(category):
        candidates = X[(y == category).to_numpy()]
        for start in range(0, min(len(candidates), 50), 10):
            chunk = candidates.iloc[start:start + 10]
            predicted = pipeline.predict(chunk)
            for i, p in enumerate(predicted):
                if p == category:
                    return chunk.iloc[i].to_dict()
        raise AssertionError(f"no validation row predicted as {category!r}")

    return find


# --- Startup and health ---------------------------------------------------


def test_application_starts_and_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True


def test_model_version_comes_from_the_metadata_artifact(client):
    metadata = client.app.state.model_service.metadata
    expected = f"{metadata['model_name']}-{metadata['saved_date']}"
    assert client.get("/health").json()["model_version"] == expected
    assert metadata["task"].startswith("multiclass")


# --- /predict: mappings (ADR-012) -----------------------------------------


def test_normal_maps_to_normal_with_null_attack_type(client, row_predicted_as):
    body = client.post(
        "/predict", json={"features": row_predicted_as("normal")}).json()
    assert body["prediction"] == "normal"
    assert body["attack_type"] is None


@pytest.mark.parametrize("category", ["dos", "probe", "r2l", "u2r"])
def test_attack_categories_map_to_attack_plus_type(client, row_predicted_as,
                                                   category):
    body = client.post(
        "/predict", json={"features": row_predicted_as(category)}).json()
    assert body["prediction"] == "attack"
    assert body["attack_type"] == category


def test_api_serves_exactly_the_serialized_m4_artifact(client, one_row):
    """The response must equal what the artifact on disk predicts itself."""
    direct = joblib.load(MODEL_FILE)
    import pandas as pd
    from src.preprocessing import FEATURE_COLUMNS
    expected_category = direct.predict(
        pd.DataFrame([one_row], columns=FEATURE_COLUMNS))[0]
    body = client.post("/predict", json={"features": one_row}).json()
    if expected_category == "normal":
        assert body["prediction"] == "normal" and body["attack_type"] is None
    else:
        assert body["prediction"] == "attack"
        assert body["attack_type"] == expected_category


# --- /predict: response contents ------------------------------------------


def test_response_schema_is_exactly_the_contract(client, one_row):
    body = client.post("/predict", json={"features": one_row}).json()
    assert set(body) == {"prediction", "attack_type", "confidence",
                         "timestamp"}


def test_confidence_is_a_probability(client, one_row):
    confidence = client.post(
        "/predict", json={"features": one_row}).json()["confidence"]
    assert 0.0 <= confidence <= 1.0


def test_timestamp_is_valid_utc_iso8601(client, one_row):
    timestamp = client.post(
        "/predict", json={"features": one_row}).json()["timestamp"]
    assert timestamp.endswith("Z")
    datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")  # raises if malformed


# --- /predict: validation (NFR6) ------------------------------------------


def test_missing_feature_returns_422(client, one_row):
    incomplete = dict(one_row)
    incomplete.pop("duration")
    assert client.post(
        "/predict", json={"features": incomplete}).status_code == 422


def test_non_numeric_value_returns_422(client, one_row):
    assert client.post(
        "/predict",
        json={"features": {**one_row, "src_bytes": "lots"}},
    ).status_code == 422


def test_unknown_field_returns_422(client, one_row):
    assert client.post(
        "/predict",
        json={"features": {**one_row, "durration": 5}},
    ).status_code == 422


def test_structurally_malformed_requests_return_422(client, one_row):
    assert client.post("/predict", json={}).status_code == 422
    assert client.post("/predict", json={"features": 7}).status_code == 422
    assert client.post("/predict", json=[one_row]).status_code == 422


def test_unknown_categorical_value_is_handled_not_crashed(client, one_row):
    """M2's handle_unknown='ignore': a never-seen service must still predict."""
    response = client.post(
        "/predict",
        json={"features": {**one_row, "service": "service_from_the_future"}})
    assert response.status_code == 200
    assert response.json()["prediction"] in ("normal", "attack")


def test_validation_errors_do_not_break_later_requests(client, one_row):
    client.post("/predict", json={"features": {"nonsense": True}})
    assert client.post(
        "/predict", json={"features": one_row}).status_code == 200


def test_numeric_fields_are_strict_json_numbers(client, one_row):
    """Audit finding: lax mode silently coerced "181" and true into model
    input while the docs promised 422. Numbers stay accepted (int or float);
    strings and booleans are rejected."""
    ok = client.post(
        "/predict", json={"features": {**one_row, "src_bytes": 181}})
    assert ok.status_code == 200
    for bad_value in ("181", True):
        response = client.post(
            "/predict", json={"features": {**one_row, "src_bytes": bad_value}})
        assert response.status_code == 422, bad_value


def test_finite_float_beyond_float32_range_returns_422(client, one_row):
    """Audit finding: 1e308 passed validation, overflowed the pipeline's
    float32 cast and produced a 500. The schema bound turns it into 422."""
    for bad_value in (1e308, 3.5e38, -1e39):
        response = client.post(
            "/predict", json={"features": {**one_row, "src_bytes": bad_value}})
        assert response.status_code == 422, bad_value
    within_range = client.post(
        "/predict", json={"features": {**one_row, "src_bytes": 3.4e38}})
    assert within_range.status_code == 200


def test_json_nan_and_infinity_literals_return_422(client, one_row):
    """Audit finding: stdlib json parses the non-standard NaN/Infinity
    tokens; the default 422 handler then crashed rendering them (500).
    The sanitizing handler must answer a clean 422."""
    template = dict(one_row)
    template.pop("src_bytes")
    import json as jsonlib
    base = jsonlib.dumps({"features": {**template, "src_bytes": 0}})
    for literal in ("NaN", "Infinity", "-Infinity", "1e400"):
        payload = base.replace('"src_bytes": 0', f'"src_bytes": {literal}')
        response = client.post(
            "/predict", content=payload,
            headers={"content-type": "application/json"})
        assert response.status_code == 422, literal
        assert response.json()["detail"]  # field-level info survives


def test_deeply_nested_body_returns_422_not_recursion_error(client):
    """Audit finding: the default handler recursed over the echoed input and
    hit the recursion limit (500) on a ~12 KB crafted body."""
    nested = jsonloads_bomb = "[" * 6000 + "]" * 6000
    response = client.post(
        "/predict", content=f'{{"features": {nested}}}',
        headers={"content-type": "application/json"})
    assert response.status_code == 422
    assert jsonloads_bomb not in response.text  # input is not echoed back


@needs_artifact
def test_internal_prediction_error_returns_500_not_crash(one_row):
    """If prediction itself blows up the app must answer 500 and keep serving
    (separate client: raise_server_exceptions=False, and no shared state)."""
    from api.main import app
    with TestClient(app, raise_server_exceptions=False) as crash_client:
        with patch.object(crash_client.app.state.model_service, "predict",
                          side_effect=RuntimeError("boom")):
            assert crash_client.post(
                "/predict", json={"features": one_row}).status_code == 500
        assert crash_client.get("/health").status_code == 200
        assert crash_client.post(
            "/predict", json={"features": one_row}).status_code == 200


# --- Model loading discipline ---------------------------------------------


def test_model_is_not_reloaded_per_request(client, one_row):
    with patch("api.model_service.joblib.load") as load_spy:
        for _ in range(3):
            assert client.post(
                "/predict", json={"features": one_row}).status_code == 200
        load_spy.assert_not_called()


def test_binary_m3_artifact_is_never_referenced_by_api_code():
    """ADR-012: /predict serves the multi-class pipeline ONLY."""
    for module in Path(api_pkg.__file__).parent.glob("*.py"):
        text = module.read_text(encoding="utf-8")
        assert "binary_pipeline" not in text, module
    assert MODEL_FILE.name == "multiclass_pipeline.joblib"


def test_api_code_never_reads_kddtest(client):
    """Same isolation rule as src/: the API cannot touch KDDTest+. It needs
    no dataset access at all — the request body is its only input."""
    for module in Path(api_pkg.__file__).parent.glob("*.py"):
        text = module.read_text(encoding="utf-8")
        assert "TEST_FILE" not in text, module
        assert "KDDTest" not in text, module
        assert "load_nslkdd" not in text, module


# --- /stats ----------------------------------------------------------------


def test_stats_starts_from_zero_state(client):
    body = client.get("/stats").json()
    assert body == {"total_flows": 0, "normal_count": 0, "attack_count": 0,
                    "attacks_by_type": {"dos": 0, "probe": 0, "r2l": 0,
                                        "u2r": 0},
                    "traffic_timeline": []}


def test_stats_reflect_predictions(client, row_predicted_as):
    client.post("/predict", json={"features": row_predicted_as("normal")})
    client.post("/predict", json={"features": row_predicted_as("dos")})
    client.post("/predict", json={"features": row_predicted_as("dos")})
    body = client.get("/stats").json()
    assert body["total_flows"] == 3
    assert body["normal_count"] == 1
    assert body["attack_count"] == 2
    assert body["attacks_by_type"]["dos"] == 2
    timeline = body["traffic_timeline"]
    assert sum(m["normal"] for m in timeline) == 1
    assert sum(m["attack"] for m in timeline) == 2


# --- /predictions/recent ---------------------------------------------------


def test_recent_returns_newest_first_with_features(client, row_predicted_as):
    normal_row = row_predicted_as("normal")
    dos_row = row_predicted_as("dos")
    client.post("/predict", json={"features": normal_row})
    client.post("/predict", json={"features": dos_row})
    records = client.get("/predictions/recent").json()
    assert len(records) == 2
    assert records[0]["prediction"] == "attack"     # newest first
    assert records[1]["prediction"] == "normal"
    assert set(records[0]) == {"prediction", "attack_type", "confidence",
                               "timestamp", "features"}
    assert records[0]["features"]["service"] == dos_row["service"]


def test_recent_limit_parameter(client, one_row):
    for _ in range(3):
        client.post("/predict", json={"features": one_row})
    assert len(client.get("/predictions/recent?limit=2").json()) == 2
    assert client.get("/predictions/recent?limit=0").status_code == 422


def test_recent_limit_cannot_exceed_maximum(client):
    from api.main import MAX_RECENT_LIMIT
    assert MAX_RECENT_LIMIT <= HISTORY_LIMIT
    assert client.get(
        f"/predictions/recent?limit={MAX_RECENT_LIMIT + 1}"
    ).status_code == 422


# --- Bounded state ---------------------------------------------------------


def test_history_is_bounded_but_counters_are_lifetime():
    history = PredictionHistory()
    for i in range(HISTORY_LIMIT + 25):
        history.add({"prediction": "attack", "attack_type": "dos",
                     "confidence": 0.9,
                     "timestamp": "2026-08-26T10:00:00Z", "features": {}})
    assert len(history.recent(HISTORY_LIMIT * 2)) == HISTORY_LIMIT
    assert history.stats()["total_flows"] == HISTORY_LIMIT + 25


def test_timeline_is_bounded_to_its_window():
    from api.state import TIMELINE_MINUTES
    history = PredictionHistory()
    for hour in range(2):
        for minute in range(60):
            history.add({"prediction": "normal", "attack_type": None,
                         "confidence": 0.5,
                         "timestamp": f"2026-08-26T{hour:02d}:{minute:02d}:00Z",
                         "features": {}})
    assert len(history.stats()["traffic_timeline"]) == TIMELINE_MINUTES


def test_timeline_keeps_same_wall_minute_on_different_days_apart():
    """Audit finding: an HH:MM-only key merged yesterday's 10:14 traffic
    into today's bucket on a long-lived server."""
    history = PredictionHistory()
    for day in ("25", "26"):
        history.add({"prediction": "normal", "attack_type": None,
                     "confidence": 0.5,
                     "timestamp": f"2026-08-{day}T10:14:00Z", "features": {}})
    timeline = history.stats()["traffic_timeline"]
    assert len(timeline) == 2
    assert all(entry["minute"] == "10:14" and entry["normal"] == 1
               for entry in timeline)


def test_restart_semantics_reset_history(client, one_row):
    client.post("/predict", json={"features": one_row})
    client.app.state.history.reset()   # what a process restart does
    assert client.get("/stats").json()["total_flows"] == 0


# --- Latency (NFR1) --------------------------------------------------------


def test_warm_prediction_latency_under_200ms(client, one_row):
    import time
    for _ in range(3):  # warm-up
        client.post("/predict", json={"features": one_row})
    timings = []
    for _ in range(20):
        started = time.perf_counter()
        client.post("/predict", json={"features": one_row})
        timings.append(time.perf_counter() - started)
    median_ms = sorted(timings)[len(timings) // 2] * 1000
    assert median_ms < 200, f"median warm latency {median_ms:.1f} ms"
