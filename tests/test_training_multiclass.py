"""Milestone-4 verification: multi-class pipelines, output domain, serialization.

Model-fit tests use the shared small stratified sample (tests/conftest.py) so
the suite stays fast while exercising real data through the real pipelines.
KDDTest+ isolation needs no new test here: the M3 source-scan test globs every
module in src/training and src/evaluation, so the M4 modules are covered
automatically.
"""

import json

import joblib
import numpy as np
import pytest
from scipy import sparse
from sklearn.preprocessing import StandardScaler

from src.config import ATTACK_CATEGORIES, MODELS_DIR
from src.preprocessing import split_features_target
from src.training.multiclass import (
    CATEGORY_ORDER,
    MULTICLASS_MODEL_NAMES,
    build_multiclass_pipeline,
    densify,
)

# --- Fixtures (sample_frames comes from tests/conftest.py) ----------------


@pytest.fixture(scope="session")
def fitted_small_forest(sample_frames):
    sample_train, _ = sample_frames
    X, y = split_features_target(sample_train, "multiclass")
    return build_multiclass_pipeline("random_forest").fit(X, y)


# --- Class universe -------------------------------------------------------


def test_category_order_covers_exactly_the_dataset_categories():
    assert set(CATEGORY_ORDER) == {"normal"} | set(ATTACK_CATEGORIES.values())
    assert len(CATEGORY_ORDER) == 5


# --- Pipeline construction ------------------------------------------------


def test_pipelines_pair_preprocessor_with_classifier():
    for name in MULTICLASS_MODEL_NAMES:
        steps = list(build_multiclass_pipeline(name).named_steps)
        assert steps[0] == "preprocessor"
        assert steps[-1] == "classifier"


def test_scaling_matches_model_family():
    def numeric_branch(pipeline):
        transformers = pipeline.named_steps["preprocessor"].transformers
        return dict((n, t) for n, t, _ in transformers)["numeric"]

    logreg = build_multiclass_pipeline("logistic_regression")
    assert isinstance(numeric_branch(logreg), StandardScaler)
    for tree_model in ("random_forest", "hist_gradient_boosting"):
        assert numeric_branch(build_multiclass_pipeline(tree_model)) \
            == "passthrough"


def test_hist_gradient_boosting_gets_densify_step():
    """HGB requires dense input; the other models keep the sparse matrix."""
    hgb = build_multiclass_pipeline("hist_gradient_boosting")
    assert "densify" in hgb.named_steps
    assert "densify" not in build_multiclass_pipeline("random_forest").named_steps


def test_densify_converts_sparse_and_passes_dense_through():
    matrix = sparse.csr_matrix(np.eye(3))
    dense = densify(matrix)
    assert not sparse.issparse(dense)
    assert np.array_equal(dense, np.eye(3))
    already_dense = np.ones((2, 2))
    assert densify(already_dense) is already_dense


def test_unknown_model_name_rejected():
    with pytest.raises(ValueError, match="model_name"):
        build_multiclass_pipeline("xgboost")


# --- Training and prediction ----------------------------------------------


@pytest.mark.parametrize("model_name", MULTICLASS_MODEL_NAMES)
def test_training_produces_valid_category_predictions(model_name,
                                                      sample_frames):
    sample_train, sample_val = sample_frames
    X_train, y_train = split_features_target(sample_train, "multiclass")
    X_val, _ = split_features_target(sample_val, "multiclass")
    pipeline = build_multiclass_pipeline(model_name).fit(X_train, y_train)
    predictions = pipeline.predict(X_val)
    assert predictions.shape == (len(X_val),)
    assert set(np.unique(predictions)) <= set(CATEGORY_ORDER)


def test_predict_proba_is_a_valid_distribution_over_5_classes(
        fitted_small_forest, sample_frames):
    _, sample_val = sample_frames
    X_val, _ = split_features_target(sample_val, "multiclass")
    probabilities = fitted_small_forest.predict_proba(X_val)
    assert probabilities.shape == (len(X_val), 5)
    assert not np.isnan(probabilities).any()
    assert ((probabilities >= 0) & (probabilities <= 1)).all()
    assert np.allclose(probabilities.sum(axis=1), 1.0)
    assert set(fitted_small_forest.named_steps["classifier"].classes_) \
        == set(CATEGORY_ORDER)


# --- Serialization --------------------------------------------------------


def test_save_reload_produces_identical_predictions(fitted_small_forest,
                                                    sample_frames, tmp_path):
    _, sample_val = sample_frames
    X_val, _ = split_features_target(sample_val, "multiclass")
    artifact = tmp_path / "pipeline.joblib"
    joblib.dump(fitted_small_forest, artifact)
    reloaded = joblib.load(artifact)
    assert np.array_equal(reloaded.predict(X_val),
                          fitted_small_forest.predict(X_val))
    assert list(reloaded.named_steps["preprocessor"].get_feature_names_out()) \
        == list(fitted_small_forest.named_steps["preprocessor"]
                .get_feature_names_out())


def test_production_artifact_loads_and_metadata_matches():
    """Sanity of the REAL serialized production candidate, when present.

    The .joblib is gitignored (fresh clones regenerate it via
    `python -m src.training.train_multiclass --save random_forest`), so this
    test skips rather than fails when the artifact is absent.
    """
    artifact = MODELS_DIR / "multiclass_pipeline.joblib"
    metadata_file = MODELS_DIR / "multiclass_metadata.json"
    if not artifact.exists():
        pytest.skip("multiclass_pipeline.joblib not built on this machine")
    pipeline = joblib.load(artifact)
    assert set(pipeline.named_steps["classifier"].classes_) \
        == set(CATEGORY_ORDER)
    with open(metadata_file, encoding="utf-8") as handle:
        metadata = json.load(handle)
    assert metadata["model_name"] in MULTICLASS_MODEL_NAMES
    assert set(metadata["classes"]) == set(CATEGORY_ORDER)
    assert metadata["random_state"] == 42
