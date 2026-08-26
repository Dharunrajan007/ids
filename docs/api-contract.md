# API Contract v1 (frozen before backend implementation)

Base URL (local demo): `http://localhost:8000`

Changes to this contract require a new ADR in [DECISIONS.md](DECISIONS.md).

## POST /predict — classify one flow

**Request**
```jsonc
{
  "features": {
    "duration": 0,
    "protocol_type": "tcp",
    "service": "http",
    "flag": "SF",
    "src_bytes": 181,
    "dst_bytes": 5450
    // ... all remaining NSL-KDD features; exact required list is frozen
    // in Milestone 2 once preprocessing determines which columns are used
  }
}
```

**Response 200**
```jsonc
{
  "prediction": "attack",          // "normal" | "attack"
  "attack_type": "dos",            // "dos" | "probe" | "r2l" | "u2r" | null when normal
  "confidence": 0.96,              // max class probability, 0-1
  "timestamp": "2026-07-28T10:15:02Z"
}
```

**Response 422** — automatic (Pydantic) on missing/invalid fields, with field-level error details.

## GET /stats — dashboard counters and chart data

```jsonc
{
  "total_flows": 1240,
  "normal_count": 1051,
  "attack_count": 189,
  "attacks_by_type": { "dos": 150, "probe": 30, "r2l": 7, "u2r": 2 },
  "traffic_timeline": [ { "minute": "10:14", "normal": 55, "attack": 9 } ]
}
```

## GET /predictions/recent?limit=50 — live feed

Array of items, newest first. Each item = the `/predict` response **plus** the
submitted features, so the dashboard detail panel needs no extra endpoint.

## GET /health

```jsonc
{ "status": "ok", "model_loaded": true, "model_version": "..." }
```

## Notes

- The API keeps recent predictions in a **bounded in-memory list** (no database,
  per project constraints). History resets when the API restarts — acceptable for a demo.
- Dashboard polls `/stats` and `/predictions/recent` every 2 seconds (ADR-007).

## Implementation clarifications (recorded at M5, 2026-08-26; the two
## client-visible bounds are covered by ADR-014)

- The `/predict` feature list is the 40-column M2 allow-list; the request
  schema is generated from `src.preprocessing.FEATURE_COLUMNS`
  (`protocol_type`/`service`/`flag` strings, the other 37 numeric). Numeric
  fields are STRICT finite JSON numbers within float32 range (±3.4e38):
  missing/extra fields, strings, booleans, NaN/Infinity, or larger
  magnitudes → 422 (ADR-014). Validation errors never echo the raw input
  back. Unknown categorical *values* are accepted
  (M2 `handle_unknown="ignore"`).
- `confidence` is the model's maximum class probability and is
  **UNCALIBRATED** (Random Forest vote fraction) — a relative score, not the
  probability the prediction is correct.
- `timestamp` is server-generated UTC, second precision, `Z` suffix.
- `model_version` = `<model_name>-<saved_date>` from
  `models/multiclass_metadata.json` (e.g. `random_forest-2026-08-26`).
- `/predictions/recent`: `limit` defaults to 50, allowed range 1-500 (422
  outside it); records are newest first.
- Bounded state sizes: last 1,000 prediction records; `traffic_timeline`
  covers the most recent 60 minutes seen, keyed `"HH:MM"` (UTC); the
  `/stats` counters are lifetime-since-startup and survive records falling
  off the bounded list.
- CORS allows only the Vite dev origins (`http://localhost:5173`,
  `http://127.0.0.1:5173`) so the M6 dashboard can call the API from a
  browser; no other origin is allowed.
