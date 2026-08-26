"""Shared test fixtures. The dataset load and the stratified split are the
expensive parts, so they are session-scoped and shared across test modules.
"""

import pytest

from src.data_loader import load_nslkdd
from src.preprocessing import train_validation_split


@pytest.fixture(scope="session")
def train_frame():
    return load_nslkdd("train")


@pytest.fixture(scope="session")
def split_frames(train_frame):
    return train_validation_split(train_frame)


@pytest.fixture(scope="session")
def sample_frames(split_frames):
    """Small stratified sample: up to 400 rows per category from the training
    split (all 5 categories represented), 1,000 validation rows. Shared by the
    M3 and M4 training tests so model-fit tests stay fast on real data."""
    train_df, val_df = split_frames
    return train_df.groupby("category").head(400), val_df.head(1000)
