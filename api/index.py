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
        "service": "checkout",
        "latency_ms": 167.32,
        "uptime_pct": 99.404,
        "timestamp": 20250301
    },
    {
        "region": "apac",
        "service": "checkout",
        "latency_ms": 206.22,
        "uptime_pct": 97.976,
        "timestamp": 20250302
    },
    {
        "region": "apac",
        "service": "checkout",
        "latency_ms": 183.05,
        "uptime_pct": 98.723,
        "timestamp": 20250303
    },
    {
        "region": "apac",
        "service": "analytics",
        "latency_ms": 189.58,
        "uptime_pct": 97.508,
        "timestamp": 20250304
    },
    {
        "region": "apac",
        "service": "catalog",
        "latency_ms": 158.91,
        "uptime_pct": 97.437,
        "timestamp": 20250305
    },
    {
        "region": "apac",
        "service": "recommendations",
        "latency_ms": 144.33,
        "uptime_pct": 97.524,
        "timestamp": 20250306
    },
    {
        "region": "apac",
        "service": "payments",
        "latency_ms": 172.3,
        "uptime_pct": 98.906,
        "timestamp": 20250307
    },
    {
        "region": "apac",
        "service": "analytics",
        "latency_ms": 138.87,
        "uptime_pct": 97.198,
        "timestamp": 20250308
    },
    {
        "region": "apac",
        "service": "analytics",
        "latency_ms": 196.37,
        "uptime_pct": 97.852,
        "timestamp": 20250309
    },
    {
        "region": "apac",
        "service": "payments",
        "latency_ms": 220.18,
        "uptime_pct": 98.454,
        "timestamp": 20250310
    },
    {
        "region": "apac",
        "service": "analytics",
        "latency_ms": 187.98,
        "uptime_pct": 99.464,
        "timestamp": 20250311
    },
    {
        "region": "apac",
        "service": "recommendations",
        "latency_ms": 171.78,
        "uptime_pct": 97.326,
        "timestamp": 20250312
    },
    {
        "region": "emea",
        "service": "checkout",
        "latency_ms": 118.68,
        "uptime_pct": 97.347,
        "timestamp": 20250301
    },
    {
        "region": "emea",
        "service": "analytics",
        "latency_ms": 142.42,
        "uptime_pct": 97.251,
        "timestamp": 20250302
    },
    {
        "region": "emea",
        "service": "support",
        "latency_ms": 152.16,
        "uptime_pct": 98.187,
        "timestamp": 20250303
    },
    {
        "region": "emea",
        "service": "recommendations",
        "latency_ms": 121.68,
        "uptime_pct": 97.473,
        "timestamp": 20250304
    },
    {
        "region": "emea",
        "service": "analytics",
        "latency_ms": 218.73,
        "uptime_pct": 97.117,
        "timestamp": 20250305
    },
    {
        "region": "emea",
        "service": "checkout",
        "latency_ms": 193.85,
        "uptime_pct": 97.488,
        "timestamp": 20250306
    },
    {
        "region": "emea",
        "service": "support",
        "latency_ms": 178.26,
        "uptime_pct": 98.351,
        "timestamp": 20250307
    },
    {
        "region": "emea",
        "service": "support",
        "latency_ms": 132.64,
        "uptime_pct": 97.13,
        "timestamp": 20250308
    },
    {
        "region": "emea",
        "service": "recommendations",
        "latency_ms": 125.98,
        "uptime_pct": 98.61,
        "timestamp": 20250309
    },
    {
        "region": "emea",
        "service": "payments",
        "latency_ms": 190.89,
        "uptime_pct": 97.105,
        "timestamp": 20250310
    },
    {
        "region": "emea",
        "service": "support",
        "latency_ms": 225.83,
        "uptime_pct": 97.49,
        "timestamp": 20250311
    },
    {
        "region": "emea",
        "service": "support",
        "latency_ms": 160.7,
        "uptime_pct": 98.333,
        "timestamp": 20250312
    },
    {
        "region": "amer",
        "service": "analytics",
        "latency_ms": 172.43,
        "uptime_pct": 97.456,
        "timestamp": 20250301
    },
    {
        "region": "amer",
        "service": "checkout",
        "latency_ms": 147.72,
        "uptime_pct": 99.354,
        "timestamp": 20250302
    },
    {
        "region": "amer",
        "service": "support",
        "latency_ms": 191.88,
        "uptime_pct": 98.501,
        "timestamp": 20250303
    },
    {
        "region": "amer",
        "service": "checkout",
        "latency_ms": 191.83,
        "uptime_pct": 98.564,
        "timestamp": 20250304
    },
    {
        "region": "amer",
        "service": "recommendations",
        "latency_ms": 170.79,
        "uptime_pct": 97.144,
        "timestamp": 20250305
    },
    {
        "region": "amer",
        "service": "recommendations",
        "latency_ms": 175.1,
        "uptime_pct": 99.466,
        "timestamp": 20250306
    },
    {
        "region": "amer",
        "service": "payments",
        "latency_ms": 195.75,
        "uptime_pct": 97.162,
        "timestamp": 20250307
    },
    {
        "region": "amer",
        "service": "analytics",
        "latency_ms": 199.23,
        "uptime_pct": 98.66,
        "timestamp": 20250308
    },
    {
        "region": "amer",
        "service": "payments",
        "latency_ms": 176.8,
        "uptime_pct": 98.645,
        "timestamp": 20250309
    },
    {
        "region": "amer",
        "service": "analytics",
        "latency_ms": 238.7,
        "uptime_pct": 99.038,
        "timestamp": 20250310
    },
    {
        "region": "amer",
        "service": "recommendations",
        "latency_ms": 164.89,
        "uptime_pct": 98.887,
        "timestamp": 20250311
    },
    {
        "region": "amer",
        "service": "catalog",
        "latency_ms": 206.39,
        "uptime_pct": 98.842,
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
