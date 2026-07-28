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
