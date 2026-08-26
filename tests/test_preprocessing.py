"""Milestone-2 verification: preprocessing, split, and leakage guarantees.

Run from the project root:  python -m pytest

The expensive dataset load and preprocessor fit happen once per session
(fixtures below); individual tests stay focused and cheap.
"""

from pathlib import Path

import numpy as np
import pytest
from scipy import sparse
from sklearn.preprocessing import StandardScaler

import src.preprocessing as preprocessing_pkg
from src.data_loader import load_nslkdd
from src.preprocessing import (
    DROPPED_FEATURES,
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURES,
    NUMERIC_FEATURES,
    build_preprocessor,
    split_features_target,
    train_validation_split,
)

# --- Shared fixtures ------------------------------------------------------


@pytest.fixture(scope="session")
def train_frame():
    return load_nslkdd("train")


@pytest.fixture(scope="session")
def split_frames(train_frame):
    return train_validation_split(train_frame)


@pytest.fixture(scope="session")
def fitted(split_frames):
    """Preprocessor (scaling='none') fitted on the TRAINING split only."""
    train_df, _ = split_frames
    X_train, _ = split_features_target(train_df, "multiclass")
    pre = build_preprocessor(scaling="none")
    X_transformed = pre.fit_transform(X_train)
    return pre, X_transformed


def _dense(matrix):
    return matrix.toarray() if sparse.issparse(matrix) else np.asarray(matrix)


def _column(pre, matrix, feature_name):
    idx = list(pre.get_feature_names_out()).index(feature_name)
    return _dense(matrix[:, [idx]]).ravel()


# --- Feature/target separation and leakage -------------------------------


@pytest.mark.parametrize("task,target", [("binary", "is_attack"),
                                         ("multiclass", "category")])
def test_feature_matrix_excludes_forbidden_columns(train_frame, task, target):
    X, y = split_features_target(train_frame, task)
    assert list(X.columns) == FEATURE_COLUMNS
    assert y.name == target
    for banned in FORBIDDEN_FEATURES + DROPPED_FEATURES:
        assert banned not in X.columns


def test_num_outbound_cmds_is_dropped():
    assert "num_outbound_cmds" in DROPPED_FEATURES
    assert "num_outbound_cmds" not in FEATURE_COLUMNS


def test_unknown_task_rejected(train_frame):
    with pytest.raises(ValueError, match="task"):
        split_features_target(train_frame, "regression")


def test_preprocessing_package_never_reads_the_test_split():
    """KDDTest+ isolation: no code in src/preprocessing can load it."""
    package_dir = Path(preprocessing_pkg.__file__).parent
    for module in package_dir.glob("*.py"):
        text = module.read_text(encoding="utf-8")
        assert "TEST_FILE" not in text, module
        assert 'load_nslkdd("test")' not in text, module
        assert "load_nslkdd('test')" not in text, module


# --- Preprocessor construction and transform ------------------------------


def test_fit_transform_width_matches_fitted_vocabulary(fitted, split_frames):
    pre, X_transformed = fitted
    train_df, _ = split_frames
    ohe = pre.named_transformers_["categorical"]
    expected_width = (sum(len(c) for c in ohe.categories_)  # one-hot block
                      + 1                                   # su_attempted
                      + len(NUMERIC_FEATURES))
    assert X_transformed.shape == (len(train_df), expected_width)


def test_validation_transforms_without_refit_and_same_width(fitted,
                                                            split_frames):
    pre, X_transformed = fitted
    _, val_df = split_frames
    X_val, _ = split_features_target(val_df, "multiclass")
    X_val_t = pre.transform(X_val)  # transform only — never fit
    assert X_val_t.shape == (len(val_df), X_transformed.shape[1])


@pytest.mark.parametrize("scaling", ["none", "standard"])
def test_no_nan_introduced(split_frames, scaling):
    train_df, val_df = split_frames
    pre = build_preprocessor(scaling=scaling)
    X_train_t = pre.fit_transform(split_features_target(train_df,
                                                        "multiclass")[0])
    X_val_t = pre.transform(split_features_target(val_df, "multiclass")[0])
    for matrix in (X_train_t, X_val_t):
        data = matrix.data if sparse.issparse(matrix) else np.asarray(matrix)
        assert not np.isnan(data).any()


def test_scaling_none_passes_numerics_through_unchanged(fitted, split_frames):
    pre, X_transformed = fitted
    train_df, _ = split_frames
    count_col = _column(pre, X_transformed, "numeric__count")
    assert np.array_equal(count_col, train_df["count"].to_numpy(dtype=float))


def test_scaling_standard_uses_standard_scaler():
    pre = build_preprocessor(scaling="standard")
    branches = dict((name, transformer)
                    for name, transformer, _ in pre.transformers)
    assert isinstance(branches["numeric"], StandardScaler)
    assert isinstance(branches["su_attempted"].named_steps["scale"],
                      StandardScaler)


def test_standard_scaling_standardizes_train_numerics(split_frames):
    train_df, _ = split_frames
    pre = build_preprocessor(scaling="standard")
    X_t = pre.fit_transform(split_features_target(train_df, "multiclass")[0])
    count_col = _column(pre, X_t, "numeric__count")
    assert abs(count_col.mean()) < 1e-9
    assert abs(count_col.std() - 1.0) < 1e-6


def test_minmax_and_other_scalings_rejected():
    for bad in ("minmax", "MinMaxScaler", "", None):
        with pytest.raises(ValueError, match="scaling"):
            build_preprocessor(scaling=bad)


# --- su_attempted domain repair -------------------------------------------


def test_su_attempted_domain_restored(fitted, train_frame):
    pre, _ = fitted
    out_of_spec = train_frame[train_frame["su_attempted"] == 2]
    assert len(out_of_spec) == 59  # count verified at M1 closeout
    X, _ = split_features_target(out_of_spec, "multiclass")
    repaired = _column(pre, pre.transform(X), "su_attempted__su_attempted")
    assert (repaired == 1).all()


def test_su_attempted_stays_binary_across_full_train(fitted, train_frame):
    pre, _ = fitted
    X, _ = split_features_target(train_frame, "multiclass")
    values = _column(pre, pre.transform(X), "su_attempted__su_attempted")
    assert set(np.unique(values)) <= {0.0, 1.0}


# --- Unknown categorical values -------------------------------------------


def test_unknown_categorical_value_transforms_to_zero_block(fitted,
                                                            split_frames):
    pre, _ = fitted
    _, val_df = split_frames
    X, _ = split_features_target(val_df.head(1).copy(), "multiclass")
    X["service"] = "service_from_the_future"
    X_t = pre.transform(X)  # must not raise
    names = pre.get_feature_names_out()
    service_block = [i for i, n in enumerate(names)
                     if n.startswith("categorical__service_")]
    assert _dense(X_t)[0, service_block].sum() == 0


# --- Train/validation split -----------------------------------------------


def test_split_is_reproducible(train_frame):
    first_train, first_val = train_validation_split(train_frame)
    second_train, second_val = train_validation_split(train_frame)
    assert first_train.index.equals(second_train.index)
    assert first_val.index.equals(second_val.index)


def test_split_is_stratified_by_category(train_frame, split_frames):
    train_df, val_df = split_frames
    assert len(train_df) + len(val_df) == len(train_frame)
    overall = train_frame["category"].value_counts(normalize=True)
    for part in (train_df, val_df):
        proportions = part["category"].value_counts(normalize=True)
        for category in overall.index:
            assert abs(proportions[category] - overall[category]) < 0.005


def test_rare_category_represented_in_both_halves(split_frames):
    train_df, val_df = split_frames
    assert train_df["category"].value_counts()["u2r"] >= 40
    assert val_df["category"].value_counts()["u2r"] >= 9  # ~20% of 52


def test_split_rejects_frames_without_category(train_frame):
    with pytest.raises(ValueError, match="category"):
        train_validation_split(train_frame.drop(columns=["category"]))


# --- Raw data integrity ---------------------------------------------------


def test_raw_files_row_counts_unchanged():
    from src.config import TEST_FILE, TRAIN_FILE
    expected = {TRAIN_FILE: 125_973, TEST_FILE: 22_544}
    for path, rows in expected.items():
        with open(path, "rb") as handle:
            assert sum(chunk.count(b"\n")
                       for chunk in iter(lambda: handle.read(1 << 20), b"")
                       ) == rows, path.name
