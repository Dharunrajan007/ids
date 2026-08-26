"""Preprocessing construction — implements docs/preprocessing-decisions.md.

Design notes:
- Everything is expressed as scikit-learn transformers so the fitted
  preprocessor can be serialized inside ONE Pipeline with the model
  (ADR-005: train/serve parity) and later reused for anomaly-detection
  experiments without duplication.
- `split_features_target` selects columns by an explicit allow-list, so the
  targets (`is_attack`, `category`), the raw `label`, and the leaky
  `difficulty` column can never reach the feature matrix, no matter what
  extra columns the input frame carries.
- The su_attempted repair is a module-level named function (not a lambda)
  because joblib can only serialize named module attributes (ADR-009).
"""

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from src.config import CATEGORICAL_FEATURES, COLUMN_NAMES

# --- Column roles (docs/preprocessing-decisions.md §1-§4) -----------------

# Targets for each modelling task. The multi-class pipeline is the production
# model (ADR-012); the binary model is the M3 evaluated baseline.
TARGET_COLUMNS = {"binary": "is_attack", "multiclass": "category"}

# Never model features: the targets themselves, the raw label they derive
# from, and `difficulty` (encodes evaluation information — leakage).
FORBIDDEN_FEATURES = ["label", "difficulty", "is_attack", "category"]

# Constant zero across all 148,517 rows — zero information.
DROPPED_FEATURES = ["num_outbound_cmds"]

# The model-input features, in dataset order.
FEATURE_COLUMNS = [
    c for c in COLUMN_NAMES
    if c not in FORBIDDEN_FEATURES and c not in DROPPED_FEATURES
]

# Numeric features excluding su_attempted, which gets its own repair branch.
NUMERIC_FEATURES = [
    c for c in FEATURE_COLUMNS
    if c not in CATEGORICAL_FEATURES and c != "su_attempted"
]

SCALING_OPTIONS = ("none", "standard")


def split_features_target(df, task):
    """Return (X, y) for one modelling task ('binary' or 'multiclass').

    X contains exactly FEATURE_COLUMNS — forbidden and dropped columns are
    excluded by construction, and a missing feature column fails loudly.
    """
    if task not in TARGET_COLUMNS:
        raise ValueError(
            f"task must be one of {sorted(TARGET_COLUMNS)}, got {task!r}"
        )
    return df[FEATURE_COLUMNS].copy(), df[TARGET_COLUMNS[task]].copy()


def restore_su_attempted_domain(values):
    """Repair su_attempted to its documented {0, 1} domain (2 -> 1).

    The 61 out-of-spec value-2 rows are logged-in sessions where su was
    attempted and succeeded, so "su was attempted" is true for them.
    This is a domain repair, not a label shortcut — it uses no target
    information (docs/preprocessing-decisions.md §7).
    """
    return np.minimum(values, 1)


def build_preprocessor(*, scaling):
    """Build the (unfitted) preprocessing ColumnTransformer.

    scaling="none"      -> tree models: raw numeric values (scale-invariant,
                           keeps feature importances in interpretable units).
    scaling="standard"  -> scale-sensitive models (LogisticRegression, kNN,
                           SVM): StandardScaler.
    MinMaxScaler is deliberately unavailable: the 1.38-billion src_bytes
    outlier would squash the feature bulk into ~[0, 1e-7]
    (docs/preprocessing-decisions.md §8).

    Fit on TRAINING data only; transform validation/test with the fitted
    object (risk R3, evaluation protocol in docs/risk-register.md).
    """
    if scaling not in SCALING_OPTIONS:
        raise ValueError(
            f"scaling must be one of {SCALING_OPTIONS}, got {scaling!r}. "
            "MinMaxScaler is deliberately rejected — see "
            "docs/preprocessing-decisions.md §8."
        )

    def numeric_stage():
        return StandardScaler() if scaling == "standard" else "passthrough"

    su_branch = Pipeline([
        ("restore_domain", FunctionTransformer(
            restore_su_attempted_domain, feature_names_out="one-to-one",
        )),
        ("scale", numeric_stage()),
    ])

    return ColumnTransformer(
        transformers=[
            ("categorical",
             OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("su_attempted", su_branch, ["su_attempted"]),
            ("numeric", numeric_stage(), NUMERIC_FEATURES),
        ],
        # Defense in depth: any unexpected column is dropped, never passed
        # through to the model.
        remainder="drop",
    )
