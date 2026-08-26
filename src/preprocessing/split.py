"""Reproducible stratified train/validation split (evaluation protocol).

All model selection, tuning, and comparison happens on this split of
KDDTrain+. Never pass the official test split here — it is evaluated exactly
once, after every choice is locked (docs/risk-register.md).
"""

from sklearn.model_selection import train_test_split

from src.config import RANDOM_STATE


def train_validation_split(df, validation_size=0.2):
    """Split the loaded KDDTrain+ frame into (train_df, validation_df).

    Stratifies on the 5-way `category` — for binary experiments too —
    so rare categories keep proportional representation in both halves
    (U2R has only 52 rows; a plain random split could starve it).
    One shared split for every task keeps binary and multi-class results
    comparable, and RANDOM_STATE makes the split identical run-to-run.
    """
    if "category" not in df.columns:
        raise ValueError(
            "expected the loaded NSL-KDD frame with the derived 'category' "
            "column (use src.data_loader.load_nslkdd)"
        )
    return train_test_split(
        df,
        test_size=validation_size,
        stratify=df["category"],
        random_state=RANDOM_STATE,
    )
