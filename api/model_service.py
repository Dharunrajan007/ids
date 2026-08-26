"""Loads the serialized M4 pipeline once and turns feature dicts into predictions.

ADR-012: the API serves ONLY the multi-class pipeline
(models/multiclass_pipeline.joblib). The M3 binary artifact is never loaded.
ADR-005: ALL preprocessing lives inside the serialized Pipeline — this module
builds a DataFrame with the right columns and hands it over; it never encodes,
scales or repairs anything itself.
"""

import json

import joblib
import pandas as pd

from src.config import MODELS_DIR
from src.preprocessing import FEATURE_COLUMNS

MODEL_FILE = MODELS_DIR / "multiclass_pipeline.joblib"
METADATA_FILE = MODELS_DIR / "multiclass_metadata.json"


class ModelService:
    """The one model instance behind every endpoint.

    Constructed exactly once, at application startup (api.main lifespan) —
    loading the 12 MB artifact takes ~1 s, far too slow to repeat per request,
    and a single instance keeps memory flat.
    """

    def __init__(self, model_file=MODEL_FILE, metadata_file=METADATA_FILE):
        if not model_file.exists():
            raise FileNotFoundError(
                f"{model_file} not found. Build it first: "
                "python -m src.training.train_multiclass --save random_forest")
        self.pipeline = joblib.load(model_file)
        with open(metadata_file, encoding="utf-8") as handle:
            self.metadata = json.load(handle)
        # /health.model_version: which model, trained when — straight from
        # the metadata artifact, e.g. "random_forest-2026-08-26".
        self.model_version = (
            f"{self.metadata['model_name']}-{self.metadata['saved_date']}")

    def predict(self, features: dict):
        """Classify one flow. Returns (prediction, attack_type, confidence).

        The DataFrame is built with FEATURE_COLUMNS explicitly so column
        order/names always match what the pipeline was fitted on, whatever
        the dict's key order.
        """
        frame = pd.DataFrame([features], columns=FEATURE_COLUMNS)
        category = self.pipeline.predict(frame)[0]
        # Max class probability = the Random Forest's vote fraction for the
        # winning class. UNCALIBRATED — documented caveat since M1.
        confidence = float(self.pipeline.predict_proba(frame)[0].max())
        if category == "normal":
            return "normal", None, confidence
        return "attack", category, confidence
