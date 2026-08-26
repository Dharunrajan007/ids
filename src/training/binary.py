"""Binary (normal vs attack) model construction — Milestone 3.

The binary model is the M3 evaluated learning baseline. Per ADR-012 the
production /predict endpoint will serve the MULTI-CLASS pipeline built in
Milestone 4; nothing here is a serving component.

Each model is one sklearn Pipeline = shared preprocessor + classifier
(ADR-005: preprocessing and model always travel together), with the
scaling variant the model family needs (docs/preprocessing-decisions.md §8).
Configurations are sensible defaults, not tuned — hyperparameter search is
deliberately out of M3 scope.
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.config import RANDOM_STATE
from src.preprocessing import build_preprocessor

BINARY_MODEL_NAMES = ("logistic_regression", "random_forest")


def build_binary_pipeline(model_name):
    """Return an unfitted Pipeline(preprocessor -> classifier) for one model.

    logistic_regression: weighted-sum-of-evidence linear model; needs
        standardized numerics (src_bytes spans 9 orders of magnitude).
        max_iter raised from the default 100 so the solver converges —
        a convergence necessity, not tuning.
    random_forest: 100-tree voting ensemble (sklearn default); threshold
        splits are scale-invariant, so numerics stay in raw, interpretable
        units.
    """
    if model_name == "logistic_regression":
        scaling = "standard"
        classifier = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    elif model_name == "random_forest":
        scaling = "none"
        classifier = RandomForestClassifier(
            n_estimators=100, random_state=RANDOM_STATE, n_jobs=-1,
        )
    else:
        raise ValueError(
            f"model_name must be one of {BINARY_MODEL_NAMES}, got {model_name!r}"
        )
    return Pipeline([
        ("preprocessor", build_preprocessor(scaling=scaling)),
        ("classifier", classifier),
    ])


def majority_baseline(y_train, n_predictions):
    """The non-ML reference floor: always predict the most common class.

    Returns (majority_label, predictions). Any real model must clearly beat
    this — otherwise it has learned nothing (docs/m3-binary-evaluation.md).
    """
    majority_label = y_train.value_counts().idxmax()
    return majority_label, np.full(n_predictions, majority_label)
