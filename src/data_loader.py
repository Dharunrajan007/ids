"""Load NSL-KDD files as pandas DataFrames with proper column names.

Promoted out of the exploration notebook because every later milestone
(preprocessing, training, the API's test tooling) needs the same loading logic.

Usage as a quick sanity check:
    python src/data_loader.py
"""

import pandas as pd

from config import COLUMN_NAMES, TEST_FILE, TRAIN_FILE, label_to_category


def load_nslkdd(split: str = "train") -> pd.DataFrame:
    """Load the NSL-KDD train or test split.

    Adds two derived columns:
      - is_attack: 0 for normal traffic, 1 for any attack (binary target, FR2)
      - category:  normal / dos / probe / r2l / u2r    (multi-class target, FR3)
    """
    if split == "train":
        path = TRAIN_FILE
    elif split == "test":
        path = TEST_FILE
    else:
        raise ValueError(f"split must be 'train' or 'test', got {split!r}")

    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run 'python src/download_data.py' first."
        )

    df = pd.read_csv(path, names=COLUMN_NAMES)
    df["is_attack"] = (df["label"] != "normal").astype(int)
    df["category"] = df["label"].map(label_to_category)
    return df


if __name__ == "__main__":
    for split in ("train", "test"):
        df = load_nslkdd(split)
        attacks = df["is_attack"].mean() * 100
        print(f"{split}: {df.shape[0]} rows x {df.shape[1]} cols, "
              f"{attacks:.1f}% attacks")
        print(df["category"].value_counts().to_string(), "\n")
