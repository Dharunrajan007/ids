"""Pydantic request/response models for the frozen API contract.

The request feature schema is DERIVED from the M2 allow-list
(`src.preprocessing.FEATURE_COLUMNS`) rather than typed out by hand: the
40 field names and their split into 3 categorical (str) + 37 numeric (float)
come from the same constants the training pipeline used, so the API schema
cannot drift from what the serialized model expects (ADR-005 in spirit:
one source of truth).

Validation behavior (NFR6 — malformed input must 422, never crash):
- every one of the 40 features is required; missing ones → 422
- unknown/extra fields → 422 (extra="forbid", catches typos like "durration")
- numeric fields are STRICT: JSON numbers only — strings ("181") and
  booleans → 422, never silently coerced into model input
- NaN/Infinity → 422, and finite magnitudes beyond float32 range → 422:
  the Random Forest validates its input as float32, so anything above
  ±3.4e38 would overflow to infinity inside the pipeline and crash it —
  the bound turns that crash into a clean validation error
- unknown categorical VALUES (e.g. a service the model never saw) are
  deliberately accepted: the pipeline's OneHotEncoder(handle_unknown="ignore")
  encodes them as an all-zeros block instead of crashing (M2 decision §6)
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, create_model

from src.config import CATEGORICAL_FEATURES
from src.preprocessing import FEATURE_COLUMNS

ATTACK_TYPES = ("dos", "probe", "r2l", "u2r")

# Largest finite float32 — the dtype sklearn's tree code casts inputs to.
FLOAT32_MAX = 3.4028235e38

# --- Request ---------------------------------------------------------------

FeatureVector = create_model(
    "FeatureVector",
    __config__=ConfigDict(extra="forbid"),
    **{
        name: (str, ...) if name in CATEGORICAL_FEATURES
        else (float, Field(strict=True, allow_inf_nan=False,
                           ge=-FLOAT32_MAX, le=FLOAT32_MAX))
        for name in FEATURE_COLUMNS
    },
)
FeatureVector.__doc__ = (
    "One NSL-KDD flow: the exact 40 model features frozen in Milestone 2. "
    "protocol_type/service/flag are strings; everything else is numeric."
)


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: FeatureVector


# --- Responses -------------------------------------------------------------


class PredictResponse(BaseModel):
    prediction: Literal["normal", "attack"]
    attack_type: Optional[Literal["dos", "probe", "r2l", "u2r"]] = Field(
        description="Attack category; null when prediction is 'normal'.")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Maximum class probability from the model. UNCALIBRATED: "
                    "this is the Random Forest's vote fraction, not an "
                    "empirical correctness rate — treat it as a relative "
                    "score, not a guarantee.")
    timestamp: str = Field(
        description="Server-generated UTC time, ISO 8601 with Z suffix.")


class RecentPrediction(PredictResponse):
    """A /predict response plus the features that produced it — the live
    feed needs no extra detail endpoint (frozen contract)."""

    features: FeatureVector


class TimelineMinute(BaseModel):
    minute: str  # "HH:MM", UTC
    normal: int
    attack: int


class StatsResponse(BaseModel):
    total_flows: int
    normal_count: int
    attack_count: int
    attacks_by_type: dict[str, int]
    traffic_timeline: list[TimelineMinute]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
