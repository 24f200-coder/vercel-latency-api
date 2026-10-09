"""eShopCo storefront latency analytics - serverless endpoint for Vercel.

POST /api/latency  (also served at /api/ and /)
Body: {"regions": ["apac", "amer"], "threshold_ms": 161}

Returns per-region avg_latency, p95_latency, avg_uptime and breaches.

Telemetry records are EMBEDDED below (from q-vercel-latency.json) because a
serverless function cannot read files from the file system at runtime; the
JSON is also shipped alongside this file for reference.
"""

import json
import math
import os
from typing import Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Telemetry bundle -------------------------------------------------------
# Source: q-vercel-latency.json (records: region, latency_ms, uptime_pct, ...)
_TELEMETRY_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "q-vercel-latency.json")

EMBEDDED_TELEMETRY: List[dict] = [
    {
        "region": "apac",
        "service": "catalog",
        "latency_ms": 133.57,
        "uptime_pct": 97.712,
        "timestamp": 20250301
    },
    {
        "region": "apac",
        "service": "catalog",
        "latency_ms": 215.53,
        "uptime_pct": 98.664,
        "timestamp": 20250302
    },
    {
        "region": "apac",
        "service": "checkout",
        "latency_ms": 233.3,
        "uptime_pct": 98.885,
        "timestamp": 20250303
    },
    {
        "region": "apac",
        "service": "catalog",
        "latency_ms": 130.34,
        "uptime_pct": 98.37,
        "timestamp": 20250304
    },
    {
        "region": "apac",
        "service": "catalog",
        "latency_ms": 110.77,
        "uptime_pct": 98.226,
        "timestamp": 20250305
    },
    {
        "region": "apac",
        "service": "checkout",
        "latency_ms": 231.48,
        "uptime_pct": 99.37,
        "timestamp": 20250306
    },
    {
        "region": "apac",
        "service": "payments",
        "latency_ms": 116.05,
        "uptime_pct": 97.417,
        "timestamp": 20250307
    },
    {
        "region": "apac",
        "service": "analytics",
        "latency_ms": 160.74,
        "uptime_pct": 97.22,
        "timestamp": 20250308
    },
    {
        "region": "apac",
        "service": "payments",
        "latency_ms": 134.95,
        "uptime_pct": 98.048,
        "timestamp": 20250309
    },
    {
        "region": "apac",
        "service": "analytics",
        "latency_ms": 137.53,
        "uptime_pct": 98.278,
        "timestamp": 20250310
    },
    {
        "region": "apac",
        "service": "payments",
        "latency_ms": 152.26,
        "uptime_pct": 99.12,
        "timestamp": 20250311
    },
    {
        "region": "apac",
        "service": "checkout",
        "latency_ms": 146.9,
        "uptime_pct": 97.723,
        "timestamp": 20250312
    },
    {
        "region": "emea",
        "service": "support",
        "latency_ms": 200.75,
        "uptime_pct": 97.366,
        "timestamp": 20250301
    },
    {
        "region": "emea",
        "service": "analytics",
        "latency_ms": 180.08,
        "uptime_pct": 97.967,
        "timestamp": 20250302
    },
    {
        "region": "emea",
        "service": "analytics",
        "latency_ms": 177.79,
        "uptime_pct": 97.462,
        "timestamp": 20250303
    },
    {
        "region": "emea",
        "service": "recommendations",
        "latency_ms": 101.02,
        "uptime_pct": 97.948,
        "timestamp": 20250304
    },
    {
        "region": "emea",
        "service": "support",
        "latency_ms": 222.3,
        "uptime_pct": 97.385,
        "timestamp": 20250305
    },
    {
        "region": "emea",
        "service": "checkout",
        "latency_ms": 111.06,
        "uptime_pct": 98.546,
        "timestamp": 20250306
    },
    {
        "region": "emea",
        "service": "catalog",
        "latency_ms": 141.89,
        "uptime_pct": 99.045,
        "timestamp": 20250307
    },
    {
        "region": "emea",
        "service": "payments",
        "latency_ms": 182.38,
        "uptime_pct": 98.94,
        "timestamp": 20250308
    },
    {
        "region": "emea",
        "service": "payments",
        "latency_ms": 131.01,
        "uptime_pct": 99.287,
        "timestamp": 20250309
    },
    {
        "region": "emea",
        "service": "support",
        "latency_ms": 237.81,
        "uptime_pct": 97.336,
        "timestamp": 20250310
    },
    {
        "region": "emea",
        "service": "payments",
        "latency_ms": 239.62,
        "uptime_pct": 99.319,
        "timestamp": 20250311
    },
    {
        "region": "emea",
        "service": "catalog",
        "latency_ms": 224.63,
        "uptime_pct": 99.131,
        "timestamp": 20250312
    },
    {
        "region": "amer",
        "service": "support",
        "latency_ms": 176.08,
        "uptime_pct": 98.806,
        "timestamp": 20250301
    },
    {
        "region": "amer",
        "service": "support",
        "latency_ms": 216.83,
        "uptime_pct": 98.939,
        "timestamp": 20250302
    },
    {
        "region": "amer",
        "service": "catalog",
        "latency_ms": 174.61,
        "uptime_pct": 99.091,
        "timestamp": 20250303
    },
    {
        "region": "amer",
        "service": "support",
        "latency_ms": 120.5,
        "uptime_pct": 99.219,
        "timestamp": 20250304
    },
    {
        "region": "amer",
        "service": "recommendations",
        "latency_ms": 138.45,
        "uptime_pct": 99.205,
        "timestamp": 20250305
    },
    {
        "region": "amer",
        "service": "analytics",
        "latency_ms": 116.88,
        "uptime_pct": 98.028,
        "timestamp": 20250306
    },
    {
        "region": "amer",
        "service": "checkout",
        "latency_ms": 171.17,
        "uptime_pct": 97.832,
        "timestamp": 20250307
    },
    {
        "region": "amer",
        "service": "payments",
        "latency_ms": 165.23,
        "uptime_pct": 97.201,
        "timestamp": 20250308
    },
    {
        "region": "amer",
        "service": "support",
        "latency_ms": 162.38,
        "uptime_pct": 98.167,
        "timestamp": 20250309
    },
    {
        "region": "amer",
        "service": "payments",
        "latency_ms": 146.02,
        "uptime_pct": 97.991,
        "timestamp": 20250310
    },
    {
        "region": "amer",
        "service": "support",
        "latency_ms": 238.32,
        "uptime_pct": 97.761,
        "timestamp": 20250311
    },
    {
        "region": "amer",
        "service": "catalog",
        "latency_ms": 221.22,
        "uptime_pct": 98.521,
        "timestamp": 20250312
    }
]


def _load_records() -> List[dict]:
    """Prefer the bundled JSON, fall back to the embedded copy."""
    try:
        with open(_TELEMETRY_JSON, "r", encoding="utf-8") as handle:
            records = json.load(handle)
        if isinstance(records, list) and records:
            return records
    except Exception:
        pass
    return EMBEDDED_TELEMETRY


TELEMETRY: List[dict] = _load_records()

app = FastAPI(title="eShopCo latency analytics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: float = 180


def percentile(values: List[float], pct: float) -> float:
    """Percentile with linear interpolation (numpy.percentile default)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (pct / 100.0) * (len(ordered) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[int(rank)])
    return float(ordered[low] + (ordered[high] - ordered[low]) * (rank - low))


def stats_for(records: List[dict], threshold: float) -> dict:
    latencies = [float(r["latency_ms"]) for r in records]
    uptimes = [float(r.get("uptime_pct", r.get("uptime", 0.0))) for r in records]
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    p95_latency = round(percentile(latencies, 95), 2) if latencies else 0.0
    avg_uptime = round(sum(uptimes) / len(uptimes), 3) if uptimes else 0.0
    breaches = sum(1 for value in latencies if value > threshold)
    return {
        "avg_latency": avg_latency,
        "p95_latency": p95_latency,
        "avg_uptime": avg_uptime,
        "breaches": int(breaches),
    }


def records_for(region: str) -> List[dict]:
    return [r for r in TELEMETRY if str(r.get("region", "")).lower() == region.lower()]


@app.get("/")
def root() -> dict:
    return {"message": "Vercel Latency Analytics API is running."}


def _analyse(payload: LatencyRequest) -> Dict[str, dict]:
    threshold = float(payload.threshold_ms)
    return {region: stats_for(records_for(region), threshold) for region in payload.regions}


@app.post("/api/latency")
@app.post("/api")
@app.post("/api/")
@app.post("/latency")
@app.post("/")
def latency(payload: LatencyRequest) -> dict:
    per_region = _analyse(payload)
    # "regions" list (reference solution shape) plus region-keyed mapping,
    # so any reasonable consumer of the response finds what it expects.
    return {
        "regions": [
            {"region": region, **metrics} for region, metrics in per_region.items()
        ],
        **per_region,
    }
