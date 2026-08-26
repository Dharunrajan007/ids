"""FastAPI application — the Milestone 5 prediction service.

Implements the frozen contract (docs/api-contract.md) over the serialized
M4 multi-class pipeline (ADR-012). Start from the project root:

    python -m uvicorn api.main:app --port 8000

Interactive documentation: http://localhost:8000/docs
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.model_service import ModelService
from api.schemas import (
    HealthResponse,
    PredictRequest,
    PredictResponse,
    RecentPrediction,
    StatsResponse,
)
from api.state import PredictionHistory

MAX_RECENT_LIMIT = 500  # ≤ state.HISTORY_LIMIT, so a full page always exists

# The future React dashboard (M6) is served by Vite's dev server on
# localhost:5173. CORS exists ONLY so that browser origin may call this API;
# no other origin is allowed ("*" would let any web page a browser visits
# talk to the local IDS — needless exposure, and the M1 review flagged it).
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The model loads exactly ONCE, here — never per request (12 MB joblib,
    # ~1 s). Endpoints reach it through app.state.
    started = time.perf_counter()
    app.state.model_service = ModelService()
    app.state.history = PredictionHistory()
    print(f"model {app.state.model_service.model_version} loaded "
          f"in {time.perf_counter() - started:.2f}s")
    yield


app = FastAPI(
    title="IDS Prediction Service",
    description=(
        "Classifies NSL-KDD network flows with the Milestone-4 Random Forest "
        "pipeline (preprocessing + classifier in one artifact). `confidence` "
        "is the model's maximum class probability and is **uncalibrated** — "
        "a relative score, not the probability the prediction is correct. "
        "History is in-memory and bounded; it resets on restart by design."),
    version="1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_returns_422(request, exc):
    """422 with field-level detail, WITHOUT echoing the raw input back.

    FastAPI's default handler serializes each error's `input` value into the
    response. Adversarial audit showed two ways that crashes the 422 itself
    into a 500: a JSON NaN/Infinity literal (stdlib json parses them; the
    response encoder then refuses to emit them) and a deeply nested body
    (the encoder recurses over it past the recursion limit). Dropping the
    input echo keeps the useful part — which field, what's wrong — and makes
    the 422 unconditionally serializable (NFR6: malformed input never
    crashes a request).
    """
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": list(error.get("loc", [])), "msg": str(error.get("msg", "")),
         "type": str(error.get("type", ""))}
        for error in exc.errors()
    ]})


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    """Classify one flow. Validation failures return 422 before this runs."""
    features = request.features.model_dump()
    prediction, attack_type, confidence = \
        app.state.model_service.predict(features)
    response = PredictResponse(
        prediction=prediction,
        attack_type=attack_type,
        confidence=confidence,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    app.state.history.add({**response.model_dump(), "features": features})
    return response


@app.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    """Counters and per-minute timeline for the dashboard (2 s polling)."""
    return StatsResponse(**app.state.history.stats())


@app.get("/predictions/recent", response_model=list[RecentPrediction])
def recent_predictions(
    limit: int = Query(50, ge=1, le=MAX_RECENT_LIMIT,
                       description="How many records, newest first."),
) -> list[RecentPrediction]:
    """The live feed: recent predictions plus their submitted features."""
    return [RecentPrediction(**record)
            for record in app.state.history.recent(limit)]


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness + which model artifact is loaded. Runs no prediction."""
    service = getattr(app.state, "model_service", None)
    return HealthResponse(
        status="ok",
        model_loaded=service is not None,
        model_version=service.model_version if service else "",
    )
