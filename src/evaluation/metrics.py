"""Evaluation utilities shared by Milestone 3 (binary) and Milestone 4 (multi-class).

One function produces everything the project's evaluation rules require
(risk R1: never accuracy alone): confusion matrix, per-class precision/
recall/F1, and macro/weighted averages, as a plain JSON-serializable dict.
"""

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


def evaluate_predictions(y_true, y_pred, *, labels=None):
    """Evaluate predictions against ground truth.

    labels: explicit class order for the confusion matrix rows/columns;
    defaults to the sorted union of observed classes.
    Returns a dict with keys: labels, accuracy, confusion_matrix (rows =
    true class, columns = predicted class), per_class (precision/recall/
    f1/support per class), macro_avg, weighted_avg.
    """
    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))
    report = classification_report(
        y_true, y_pred, labels=labels, output_dict=True, zero_division=0,
    )
    return {
        "labels": list(labels),
        "accuracy": accuracy_score(y_true, y_pred),
        "confusion_matrix": confusion_matrix(
            y_true, y_pred, labels=labels).tolist(),
        "per_class": {str(label): report[str(label)] for label in labels},
        "macro_avg": report["macro avg"],
        "weighted_avg": report["weighted avg"],
    }


def format_confusion_matrix(result, class_names=None):
    """Render a result's confusion matrix as an aligned text table."""
    names = class_names or [str(label) for label in result["labels"]]
    width = max(9, *(len(n) for n in names)) + 2
    header = " " * width + "".join(f"{'pred ' + n:>{width}}" for n in names)
    rows = [header]
    for name, row in zip(names, result["confusion_matrix"]):
        rows.append(f"{'true ' + name:<{width}}"
                    + "".join(f"{count:>{width},}" for count in row))
    return "\n".join(rows)
