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
