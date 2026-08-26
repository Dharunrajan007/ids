"""Preprocessing layer (Milestone 2).

Implements docs/preprocessing-decisions.md: strict feature/target separation,
the su_attempted domain repair, one-hot encoding that survives unseen
categorical values, model-appropriate scaling selection, and the reproducible
5-way-stratified train/validation split.

Everything fits on training data only and is designed to be serialized inside
one Pipeline with the model (ADR-005 / ADR-009).
"""

from src.preprocessing.pipeline import (
    DROPPED_FEATURES,
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURES,
    NUMERIC_FEATURES,
    SCALING_OPTIONS,
    TARGET_COLUMNS,
    build_preprocessor,
    restore_su_attempted_domain,
    split_features_target,
)
from src.preprocessing.split import train_validation_split

__all__ = [
    "DROPPED_FEATURES",
    "FEATURE_COLUMNS",
    "FORBIDDEN_FEATURES",
    "NUMERIC_FEATURES",
    "SCALING_OPTIONS",
    "TARGET_COLUMNS",
    "build_preprocessor",
    "restore_su_attempted_domain",
    "split_features_target",
    "train_validation_split",
]
