"""Milestone-3 verification: baseline, binary pipelines, metrics, serialization.

Model-fit tests use a small stratified sample (~1.6k rows) so the suite stays
fast while still exercising real data through the real pipelines.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler

import src.evaluation as evaluation_pkg
import src.training as training_pkg
from src.evaluation.metrics import evaluate_predictions
from src.preprocessing import split_features_target
from src.training.binary import (
    BINARY_MODEL_NAMES,
    build_binary_pipeline,
    majority_baseline,
)

# --- Fixtures (sample_frames comes from tests/conftest.py) ----------------


@pytest.fixture(scope="session")
def fitted_small_logreg(sample_frames):
    sample_train, _ = sample_frames
    X, y = split_features_target(sample_train, "binary")
    return build_binary_pipeline("logistic_regression").fit(X, y)


# --- Pipeline construction ------------------------------------------------


def test_pipelines_pair_preprocessor_with_classifier():
    for name in BINARY_MODEL_NAMES:
        pipeline = build_binary_pipeline(name)
        assert list(pipeline.named_steps) == ["preprocessor", "classifier"]


def test_scaling_matches_model_family():
    def numeric_branch(pipeline):
        transformers = pipeline.named_steps["preprocessor"].transformers
        return dict((n, t) for n, t, _ in transformers)["numeric"]

    logreg = build_binary_pipeline("logistic_regression")
    assert isinstance(numeric_branch(logreg), StandardScaler)
    forest = build_binary_pipeline("random_forest")
    assert numeric_branch(forest) == "passthrough"


def test_unknown_model_name_rejected():
    with pytest.raises(ValueError, match="model_name"):
        build_binary_pipeline("neural_network")


# --- Baseline and metrics -------------------------------------------------


def test_majority_baseline_predicts_most_common_class():
    y = pd.Series([0, 0, 0, 1, 1])
    label, predictions = majority_baseline(y, 4)
    assert label == 0
    assert predictions.tolist() == [0, 0, 0, 0]


def test_evaluate_predictions_known_values():
    result = evaluate_predictions([0, 0, 1, 1], [0, 1, 1, 1], labels=[0, 1])
    assert result["accuracy"] == 0.75
    assert result["confusion_matrix"] == [[1, 1], [0, 2]]
    assert result["per_class"]["1"]["recall"] == 1.0
    assert result["per_class"]["0"]["recall"] == 0.5
    assert 0 < result["macro_avg"]["f1-score"] < 1


# --- Training and prediction ----------------------------------------------


@pytest.mark.parametrize("model_name", BINARY_MODEL_NAMES)
def test_training_produces_valid_binary_predictions(model_name, sample_frames):
    sample_train, sample_val = sample_frames
    X_train, y_train = split_features_target(sample_train, "binary")
    X_val, _ = split_features_target(sample_val, "binary")
    pipeline = build_binary_pipeline(model_name).fit(X_train, y_train)
    predictions = pipeline.predict(X_val)
    assert predictions.shape == (len(X_val),)
    assert set(np.unique(predictions)) <= {0, 1}


def test_predict_proba_is_a_valid_probability(fitted_small_logreg,
                                              sample_frames):
    _, sample_val = sample_frames
    X_val, _ = split_features_target(sample_val, "binary")
    probabilities = fitted_small_logreg.predict_proba(X_val)
    assert probabilities.shape == (len(X_val), 2)
    assert not np.isnan(probabilities).any()
    assert ((probabilities >= 0) & (probabilities <= 1)).all()
    assert np.allclose(probabilities.sum(axis=1), 1.0)


# --- Serialization --------------------------------------------------------


def test_save_reload_produces_identical_predictions(fitted_small_logreg,
                                                    sample_frames, tmp_path):
    _, sample_val = sample_frames
    X_val, _ = split_features_target(sample_val, "binary")
    artifact = tmp_path / "pipeline.joblib"
    joblib.dump(fitted_small_logreg, artifact)
    reloaded = joblib.load(artifact)
    assert np.array_equal(reloaded.predict(X_val),
                          fitted_small_logreg.predict(X_val))
    # the preprocessing vocabulary travels inside the single artifact
    assert list(reloaded.named_steps["preprocessor"].get_feature_names_out()) \
        == list(fitted_small_logreg.named_steps["preprocessor"]
                .get_feature_names_out())


# --- KDDTest+ isolation ---------------------------------------------------


def test_training_and_evaluation_never_read_the_test_split():
    for package in (training_pkg, evaluation_pkg):
        for module in Path(package.__file__).parent.glob("*.py"):
            text = module.read_text(encoding="utf-8")
            assert "TEST_FILE" not in text, module
            assert 'load_nslkdd("test")' not in text, module
            assert "load_nslkdd('test')" not in text, module
