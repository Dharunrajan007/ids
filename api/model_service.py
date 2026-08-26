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
        # Serving-time execution tuning, NOT a model change: n_jobs=-1 helps
        # big batches but costs ~40 ms of thread fan-out on a single row —
        # measured 49 ms -> 10 ms per predict_proba with byte-identical
        # probabilities. n_jobs only chooses how many threads compute the
        # same trees, so predictions cannot change.
        self.pipeline.named_steps["classifier"].set_params(n_jobs=1)
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
        # ONE pipeline pass, not two: predict() would rerun preprocessing and
        # all 100 trees just to argmax the same probabilities (sklearn's
        # ClassifierMixin.predict IS classes_[argmax(predict_proba)], first
        # class winning ties in both). Halves request latency; identical
        # output by construction.
        probabilities = self.pipeline.predict_proba(frame)[0]
        category = self.pipeline.named_steps["classifier"].classes_[
            probabilities.argmax()]
        # Max class probability = the Random Forest's vote fraction for the
        # winning class. UNCALIBRATED — documented caveat since M1.
        confidence = float(probabilities.max())
        if category == "normal":
            return "normal", None, confidence
        return "attack", category, confidence
