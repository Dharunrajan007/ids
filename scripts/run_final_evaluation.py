"""THE final locked KDDTest+ evaluation — Milestone 8. Run ONCE.

    python -m scripts.run_final_evaluation

This is the single sanctioned scoring read of KDDTest+ (evaluation protocol,
docs/risk-register.md). It deliberately lives in scripts/, OUTSIDE
src/training, src/evaluation, src/preprocessing and api/, whose source-scan
tests continue to prove those packages cannot read the test split.

What this script does NOT do, by design:
- no fit(): the serialized production pipeline is loaded and only predicts;
- no selection/tuning: every model decision was locked at M4;
- no reaction: whatever the numbers are, the model is not changed.

Results are printed and saved to models/final_test_metrics.json; from that
moment they are LOCKED FINAL RESULTS.
"""

import json
import platform
import time
from datetime import date

import joblib
import numpy as np
import sklearn

from src.config import MODELS_DIR
from src.data_loader import load_nslkdd
from src.evaluation.metrics import evaluate_predictions, format_confusion_matrix
from src.preprocessing import split_features_target

LABELS = ["normal", "dos", "probe", "r2l", "u2r"]
ARTIFACT = MODELS_DIR / "multiclass_pipeline.joblib"
RESULTS_FILE = MODELS_DIR / "final_test_metrics.json"


def main():
    if RESULTS_FILE.exists():
        raise SystemExit(
            f"{RESULTS_FILE} already exists — the final evaluation is LOCKED. "
            "Delete the file only if you can justify a re-run in writing.")

    test_df = load_nslkdd("test")  # the once-only scoring read
    X_test, y_test = split_features_target(test_df, "multiclass")
    print(f"=== FINAL LOCKED EVALUATION — KDDTest+ ({len(X_test):,} rows), "
          f"frozen artifact {ARTIFACT.name} ===")

    started = time.perf_counter()
    pipeline = joblib.load(ARTIFACT)
    load_seconds = time.perf_counter() - started

    started = time.perf_counter()
    y_pred = pipeline.predict(X_test)
    predict_seconds = time.perf_counter() - started

    result = evaluate_predictions(y_test, y_pred, labels=LABELS)

    print(f"time load {load_seconds:.2f}s  predict {predict_seconds:.2f}s "
          f"({predict_seconds / len(X_test) * 1000:.4f} ms/flow)")
    print(f"accuracy {result['accuracy']:.4f}")
    for label in LABELS:
        stats = result["per_class"][label]
        print(f"{label:<8} precision {stats['precision']:.4f}  "
              f"recall {stats['recall']:.4f}  f1 {stats['f1-score']:.4f}  "
              f"support {int(stats['support']):,}")
    print(f"macro    f1 {result['macro_avg']['f1-score']:.4f}   "
          f"weighted f1 {result['weighted_avg']['f1-score']:.4f}")
    print(format_confusion_matrix(result))

    # Binary IDS view (ADR-012 serving semantics: attack iff != normal).
    matrix = np.array(result["confusion_matrix"])
    normal = LABELS.index("normal")
    missed = int(matrix[:, normal].sum() - matrix[normal, normal])
    false_alarms = int(matrix[normal].sum() - matrix[normal, normal])
    attack_rows = int(matrix.sum() - matrix[normal].sum())
    binary_recall = 1 - missed / attack_rows
    binary_accuracy = float((matrix.sum() - missed - false_alarms) / matrix.sum())
    print(f"IDS view — missed attacks {missed:,} of {attack_rows:,} "
          f"(binary attack recall {binary_recall:.4f}); "
          f"false alarms {false_alarms:,} of {int(matrix[normal].sum()):,} "
          f"normal rows; binary accuracy {binary_accuracy:.4f}")

    record = {
        "locked": True,
        "evaluated_date": date.today().isoformat(),
        "dataset": "KDDTest+ (NSL-KDD official test split)",
        "rows_evaluated": int(len(X_test)),
        "artifact": ARTIFACT.name,
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "metrics": result,
        "binary_view": {
            "missed_attacks": missed,
            "attack_rows": attack_rows,
            "binary_attack_recall": binary_recall,
            "false_alarms": false_alarms,
            "normal_rows": int(matrix[normal].sum()),
            "binary_accuracy": binary_accuracy,
        },
        "timing": {"load_seconds": round(load_seconds, 2),
                   "predict_seconds": round(predict_seconds, 2)},
    }
    with open(RESULTS_FILE, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, default=float)
    print(f"\nLOCKED — results written to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
