# %% [markdown]
# # Milestone 1 — NSL-KDD Exploration
#
# Run this file cell-by-cell in VS Code (click "Run Cell" above each `# %%`),
# or all at once with:  `.\.venv\Scripts\python.exe notebooks\01_data_exploration.py`
#
# Goal: understand what's in the dataset before we preprocess anything.
# Findings that matter long-term are recorded in docs/data-dictionary.md.

# %% Setup — make src/ importable from the notebooks folder
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

import matplotlib.pyplot as plt
import pandas as pd

from data_loader import load_nslkdd

pd.set_option("display.max_columns", 50)

# %% Load both splits
train = load_nslkdd("train")
test = load_nslkdd("test")
print(f"train: {train.shape}, test: {test.shape}")
train.head()

# %% Binary balance — how much of the traffic is attack vs normal?
for name, df in [("train", train), ("test", test)]:
    counts = df["is_attack"].value_counts()
    print(f"{name}: normal={counts[0]} ({counts[0]/len(df):.1%}), "
          f"attack={counts[1]} ({counts[1]/len(df):.1%})")

# %% Attack categories — the multi-class target (note how rare U2R is!)
category_counts = pd.DataFrame({
    "train": train["category"].value_counts(),
    "test": test["category"].value_counts(),
}).fillna(0).astype(int)
print(category_counts)

fig, ax = plt.subplots(figsize=(8, 4))
category_counts.plot.bar(ax=ax, color=["#4c72b0", "#dd8452"])
ax.set_title("Flows per category — note the log scale: U2R is tiny")
ax.set_yscale("log")
ax.set_ylabel("flows (log)")
plt.tight_layout()
plt.show()

# %% Unseen attacks — labels in the TEST set that never appear in training.
# This is why test scores will look "low": the model must catch attacks
# it has literally never seen. That's realistic, and we report it honestly.
unseen = sorted(set(test["label"]) - set(train["label"]))
print(f"{len(unseen)} attack types appear only in the test set:\n{unseen}")

# %% Categorical features — how many distinct values each has
for col in ["protocol_type", "service", "flag"]:
    tr, te = set(train[col]), set(test[col])
    print(f"{col}: {len(tr)} values in train, "
          f"{len(te - tr)} test values unseen in train -> {sorted(te - tr)}")

# %% Numeric features — quick statistical profile
numeric = train.drop(columns=["label", "category", "difficulty", "is_attack"])
numeric = numeric.select_dtypes("number")
stats = numeric.describe().T[["mean", "std", "min", "max"]]
print(stats)

# %% Dead columns — anything constant carries zero information
constant_cols = [c for c in numeric.columns if train[c].nunique() == 1]
print(f"Constant columns (candidates to drop in Milestone 2): {constant_cols}")

# %% Feature scale problem — why we'll need scaling in Milestone 2
print(train[["duration", "src_bytes", "dst_bytes", "same_srv_rate"]].describe().T)
print("\nsrc_bytes reaches the hundreds of millions while rate features live in "
      "[0, 1] — distance-based models would ignore the small ones entirely.")
