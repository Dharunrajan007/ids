"""Milestone-7 verification: the traffic replay simulator.

All replay-loop tests use a fake `send` callable — no HTTP and no running
API. The data rule under test everywhere: only the 40 M2 features leave the
simulator, labels never do, and nothing evaluates anything.
"""

from pathlib import Path

import pandas as pd
import pytest

import simulator as simulator_pkg
from simulator.replay import (
    FORBIDDEN_PAYLOAD_FIELDS,
    ApiUnreachable,
    ReplayStats,
    RequestTimeout,
    build_payload,
    replay_payloads,
    run_replay,
)
from src.preprocessing import FEATURE_COLUMNS

# --- Payload construction (the leakage-critical part) ----------------------


def test_payload_is_exactly_the_40_feature_allow_list(train_frame):
    payload = build_payload(train_frame.iloc[0])
    assert set(payload) == set(FEATURE_COLUMNS)
    assert len(payload) == 40


def test_payload_never_contains_ground_truth(train_frame):
    payload = build_payload(train_frame.iloc[0])
    for banned in FORBIDDEN_PAYLOAD_FIELDS:
        assert banned not in payload
    # and the allow-list itself can never contain them by construction
    assert not set(FORBIDDEN_PAYLOAD_FIELDS) & set(FEATURE_COLUMNS)


def test_payload_values_are_plain_python(train_frame):
    """numpy scalars must be converted so the payload JSON-serializes."""
    import json
    payload = build_payload(train_frame.iloc[0])
    json.dumps(payload)  # raises on numpy types
    assert isinstance(payload["service"], str)


def test_replay_payloads_row_limit_and_shuffle_determinism(train_frame):
    frame = train_frame.head(50)
    first = list(replay_payloads(frame, rows=5, shuffle=True, seed=7))
    again = list(replay_payloads(frame, rows=5, shuffle=True, seed=7))
    assert len(first) == 5
    assert first == again  # seeded — the demo is repeatable
    ordered = list(replay_payloads(frame, rows=3, shuffle=False))
    expected = [build_payload(frame.iloc[i]) for i in range(3)]
    assert ordered == expected


# --- Replay loop (fake send; fake clock/sleep) -----------------------------


def fake_clock_factory():
    state = {"now": 0.0}

    def clock():
        return state["now"]

    def sleep(seconds):
        state["now"] += seconds

    return clock, sleep, state


def ok_send(prediction="normal"):
    def send(payload):
        return 200, {"prediction": prediction, "attack_type": None,
                     "confidence": 0.9, "timestamp": "t"}
    return send


PAYLOADS = [{"n": i} for i in range(6)]


def test_replay_counts_and_pacing():
    clock, sleep, state = fake_clock_factory()
    sent_at = []

    def send(payload):
        sent_at.append(state["now"])
        return ok_send("attack")(payload)

    stats = run_replay(iter(PAYLOADS), send, rate=2.0,
                       sleep=sleep, clock=clock, log=lambda *_: None)
    assert stats.sent == stats.ok == 6
    assert stats.attacks == 6
    # 2 flows/s -> requests scheduled at 0.0, 0.5, 1.0, ... exactly
    assert sent_at == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]


def test_replay_duration_cap():
    clock, sleep, _ = fake_clock_factory()
    stats = run_replay(iter([{"n": i} for i in range(1000)]), ok_send(),
                       rate=1.0, duration=4.5,
                       sleep=sleep, clock=clock, log=lambda *_: None)
    assert stats.sent == 5  # t=0..4 fit inside the 4.5 s cap


def test_timeout_skips_row_without_retry():
    clock, sleep, _ = fake_clock_factory()
    calls = []

    def send(payload):
        calls.append(payload["n"])
        if payload["n"] == 1:
            raise RequestTimeout()
        return ok_send()(payload)

    stats = run_replay(iter(PAYLOADS[:3]), send, rate=10.0,
                       sleep=sleep, clock=clock, log=lambda *_: None)
    assert calls == [0, 1, 2]  # row 1 NOT retried (may have been processed)
    assert stats.timeouts == 1
    assert stats.sent == 2


def test_unreachable_api_retries_same_row_until_it_returns():
    clock, sleep, _ = fake_clock_factory()
    attempts = {"count": 0}

    def send(payload):
        if payload["n"] == 0 and attempts["count"] < 3:
            attempts["count"] += 1
            raise ApiUnreachable()
        return ok_send()(payload)

    stats = run_replay(iter(PAYLOADS[:2]), send, rate=10.0,
                       sleep=sleep, clock=clock, log=lambda *_: None)
    assert attempts["count"] == 3       # same row retried while down
    assert stats.connection_failures == 3
    assert stats.sent == 2              # no row lost, no duplicate counted


def test_422_and_5xx_are_counted_and_replay_continues():
    responses = iter([(422, {"detail": []}), (500, {}), (200, {
        "prediction": "normal"})])
    clock, sleep, _ = fake_clock_factory()
    stats = run_replay(iter(PAYLOADS[:3]), lambda p: next(responses),
                       rate=10.0, sleep=sleep, clock=clock,
                       log=lambda *_: None)
    assert stats.rejected == 1
    assert stats.server_errors == 1
    assert stats.ok == 1
    assert stats.sent == 3


def test_keyboard_interrupt_exits_cleanly_with_stats():
    clock, sleep, _ = fake_clock_factory()

    def send(payload):
        if payload["n"] == 2:
            raise KeyboardInterrupt
        return ok_send()(payload)

    stats = run_replay(iter(PAYLOADS), send, rate=10.0,
                       sleep=sleep, clock=clock, log=lambda *_: None)
    assert isinstance(stats, ReplayStats)   # returned, not raised
    assert stats.sent == 2


def test_stats_summary_mentions_every_counter():
    text = ReplayStats(sent=5, ok=4, attacks=2, rejected=1,
                       elapsed=10.0).summary()
    for token in ("sent 5", "ok 4", "attacks observed 2", "422 1",
                  "flows/s"):
        assert token in text


# --- Scope discipline (source scans — no artifact or API needed) -----------


def test_simulator_never_touches_model_or_evaluation():
    """No model import, no artifact path, no metric — replay only."""
    banned = ("joblib", "sklearn", "models/", "multiclass_pipeline",
              "binary_pipeline", "accuracy", "precision", "recall",
              "f1", "confusion")
    for module in Path(simulator_pkg.__file__).parent.glob("*.py"):
        text = module.read_text(encoding="utf-8").lower()
        for term in banned:
            assert term not in text, f"{module.name} contains {term!r}"


def test_training_evaluation_api_still_isolated_from_kddtest():
    """The simulator MAY read KDDTest+ (replay input); everything that
    trains, evaluates, or serves still may not — unchanged by M7."""
    import api as api_pkg
    import src.evaluation as evaluation_pkg
    import src.preprocessing as preprocessing_pkg
    import src.training as training_pkg
    for package in (training_pkg, evaluation_pkg, preprocessing_pkg,
                    api_pkg):
        for module in Path(package.__file__).parent.glob("*.py"):
            text = module.read_text(encoding="utf-8")
            assert "TEST_FILE" not in text, module
            assert 'load_nslkdd("test")' not in text, module
            assert "load_nslkdd('test')" not in text, module
