"""Milestone 4 runner: train and evaluate the multi-class candidates.

Usage (from the project root):
    python -m src.training.train_multiclass                # evaluate all models
    python -m src.training.train_multiclass --save NAME    # also serialize NAME

Protocol (docs/risk-register.md): trains on the 80% stratified training split
of KDDTrain+ only, evaluates on the 20% validation split only. KDDTest+ is
never read here — final evaluation happens once, later, after all selection
is locked.

Timing lines are prefixed "time " so two runs can be diffed excluding them
(everything else is deterministic under RANDOM_STATE).
"""

import argparse
import json
import platform
import time
from datetime import date

import joblib
import numpy as np
import sklearn

from src.config import MODELS_DIR, RANDOM_STATE
from src.data_loader import load_nslkdd
from src.evaluation.metrics import evaluate_predictions, format_confusion_matrix
from src.preprocessing import split_features_target, train_validation_split
from src.training.binary import majority_baseline
from src.training.multiclass import (
    CATEGORY_ORDER,
    MULTICLASS_MODEL_NAMES,
    build_multiclass_pipeline,
)

MULTICLASS_PIPELINE_FILE = MODELS_DIR / "multiclass_pipeline.joblib"
MULTICLASS_METADATA_FILE = MODELS_DIR / "multiclass_metadata.json"

LABELS = list(CATEGORY_ORDER)


def _print_result(result):
    print(f"accuracy {result['accuracy']:.4f}")
    for label in result["labels"]:
        stats = result["per_class"][label]
        print(f"{label:<8} precision {stats['precision']:.4f}  "
              f"recall {stats['recall']:.4f}  f1 {stats['f1-score']:.4f}  "
              f"support {int(stats['support']):,}")
    print(f"macro    f1 {result['macro_avg']['f1-score']:.4f}   "
          f"weighted f1 {result['weighted_avg']['f1-score']:.4f}")
    print(format_confusion_matrix(result))


def _attack_view(result):
    """Collapse the 5x5 confusion matrix to the binary IDS view.

    Answers the two questions the alert feed lives on: how many real attacks
    were called normal (missed intrusions), and how many normal rows were
    called any attack (false alarms). Category mix-ups between attack classes
    are NOT failures here — the alert still fires (ADR-012 semantics).
    """
    matrix = np.array(result["confusion_matrix"])
    normal = result["labels"].index("normal")
    attacks_missed = int(matrix[:, normal].sum() - matrix[normal, normal])
    false_alarms = int(matrix[normal].sum() - matrix[normal, normal])
    attack_rows = int(matrix.sum() - matrix[normal].sum())
    print(f"IDS view — missed attacks (any attack class -> normal): "
          f"{attacks_missed:,} of {attack_rows:,} "
          f"({1 - attacks_missed / attack_rows:.4f} binary attack recall); "
          f"false alarms (normal -> any attack): {false_alarms:,}")


def run(save_model=None):
    train_full = load_nslkdd("train")
    train_df, val_df = train_validation_split(train_full)
    X_train, y_train = split_features_target(train_df, "multiclass")
    X_val, y_val = split_features_target(val_df, "multiclass")
    print(f"=== M4 multi-class evaluation — train {len(X_train):,} / "
          f"validation {len(X_val):,}, RANDOM_STATE={RANDOM_STATE} ===")

    print("\n--- majority baseline (not ML: always predict the most common "
          "training class) ---")
    majority_label, baseline_pred = majority_baseline(y_train, len(y_val))
    print(f"majority class: {majority_label}")
    _print_result(evaluate_predictions(y_val, baseline_pred, labels=LABELS))

    results = {}
    for name in MULTICLASS_MODEL_NAMES:
        print(f"\n--- {name} ---")
        pipeline = build_multiclass_pipeline(name)

        started = time.perf_counter()
        pipeline.fit(X_train, y_train)
        train_seconds = time.perf_counter() - started

        train_accuracy = float(np.mean(pipeline.predict(X_train) == y_train))

        started = time.perf_counter()
        y_pred = pipeline.predict(X_val)
        predict_seconds = time.perf_counter() - started

        result = evaluate_predictions(y_val, y_pred, labels=LABELS)
        print(f"time train {train_seconds:.1f}s  "
              f"time predict-validation {predict_seconds:.2f}s "
              f"({predict_seconds / len(X_val) * 1000:.4f} ms/flow)")
        print(f"train-split accuracy {train_accuracy:.4f} "
              "(compare with validation accuracy below: a large gap would "
              "signal overfitting, risk R4)")
        _print_result(result)
        _attack_view(result)
        results[name] = {
            "pipeline": pipeline,
            "evaluation": result,
            "train_accuracy": train_accuracy,
            "train_seconds": train_seconds,
            "predict_seconds": predict_seconds,
        }

    if save_model:
        _serialize(results[save_model], save_model, len(X_train), len(X_val),
                   X_val)
    return results


def _serialize(entry, model_name, n_train, n_val, X_val):
    """Save the selected pipeline + metadata, then prove the reload is exact."""
    MODELS_DIR.mkdir(exist_ok=True)
    pipeline = entry["pipeline"]
    joblib.dump(pipeline, MULTICLASS_PIPELINE_FILE)

    metadata = {
        "task": "multiclass (normal/dos/probe/r2l/u2r)",
        "role": "M4 selected model — the production candidate: per ADR-012 "
                "the M5 /predict endpoint serves THIS pipeline "
                "(prediction = 'attack' iff category != 'normal')",
        "model_name": model_name,
        "classes": list(pipeline.named_steps["classifier"].classes_),
        "saved_date": date.today().isoformat(),
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "random_state": RANDOM_STATE,
        "classifier_params": pipeline.named_steps["classifier"].get_params(),
        "training_rows": n_train,
        "validation_rows": n_val,
        "n_features_out": int(
            len(pipeline.named_steps["preprocessor"].get_feature_names_out())),
        "train_accuracy": entry["train_accuracy"],
        "validation_metrics": entry["evaluation"],
        "train_seconds": round(entry["train_seconds"], 1),
        "artifact": MULTICLASS_PIPELINE_FILE.name,
    }

    reloaded = joblib.load(MULTICLASS_PIPELINE_FILE)
    identical = np.array_equal(reloaded.predict(X_val),
                               pipeline.predict(X_val))

    # Single-flow latency through the reloaded artifact — the number that
    # matters for the /predict NFR (200 ms), measured on the exact object
    # M5 will serve. Median of 5 to keep one cold-cache outlier from
    # dominating.
    single_row = X_val.head(1)
    timings = []
    for _ in range(5):
        started = time.perf_counter()
        reloaded.predict(single_row)
        timings.append(time.perf_counter() - started)
    metadata["single_flow_ms"] = round(sorted(timings)[2] * 1000, 1)

    with open(MULTICLASS_METADATA_FILE, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, default=float)

    size_mb = MULTICLASS_PIPELINE_FILE.stat().st_size / 1_000_000
    print(f"\nsaved {MULTICLASS_PIPELINE_FILE.name} ({size_mb:.1f} MB) "
          f"+ {MULTICLASS_METADATA_FILE.name}")
    print(f"time single-flow predict (reloaded, median of 5) "
          f"{metadata['single_flow_ms']} ms")
    print(f"reload check — predictions identical on all {n_val:,} "
          f"validation rows: {identical}")
    if not identical:
        raise RuntimeError("reloaded pipeline disagrees with the fitted one")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", choices=MULTICLASS_MODEL_NAMES, default=None,
                        help="serialize this model after evaluation")
    run(save_model=parser.parse_args().save)
