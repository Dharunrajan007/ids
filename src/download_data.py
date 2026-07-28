"""Download the NSL-KDD dataset into data/raw/.

Repeatable by design (risk R6): if the raw files are ever corrupted or
deleted, running this script restores them. Uses only the standard library
so it works before ML dependencies are installed.

Usage:
    python src/download_data.py
"""

import urllib.request
from pathlib import Path

from config import DATA_RAW, TRAIN_FILE, TEST_FILE

# Mirror of the official NSL-KDD distribution (University of New Brunswick).
BASE_URL = "https://raw.githubusercontent.com/defcom17/NSL_KDD/master"

FILES = {
    TRAIN_FILE: f"{BASE_URL}/KDDTrain%2B.txt",  # %2B is the URL-encoded '+'
    TEST_FILE: f"{BASE_URL}/KDDTest%2B.txt",
}

# Known row counts of the official files — used as an integrity check.
EXPECTED_ROWS = {TRAIN_FILE: 125_973, TEST_FILE: 22_544}


def download(url: str, destination: Path) -> None:
    print(f"Downloading {destination.name} ...")
    urllib.request.urlretrieve(url, destination)
    size_mb = destination.stat().st_size / 1_000_000
    print(f"  saved to {destination} ({size_mb:.1f} MB)")


def verify(path: Path, expected_rows: int) -> None:
    with open(path, encoding="utf-8") as f:
        rows = sum(1 for _ in f)
    if rows != expected_rows:
        raise RuntimeError(
            f"{path.name}: expected {expected_rows} rows, found {rows}. "
            "The download may be corrupted — delete the file and rerun."
        )
    print(f"  verified: {rows} rows (matches official count)")


def main() -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    for destination, url in FILES.items():
        if destination.exists():
            print(f"{destination.name} already exists, skipping download.")
        else:
            download(url, destination)
        verify(destination, EXPECTED_ROWS[destination])
    print("Dataset ready.")


if __name__ == "__main__":
    main()
