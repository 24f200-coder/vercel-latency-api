"""eShopCo storefront latency analytics - serverless endpoint for Vercel.

POST /api/latency with {"regions": [...], "threshold_ms": 180} returns, for
each requested region: avg_latency, p95_latency, avg_uptime and breaches.

The telemetry records are embedded at build time (see TELEMETRY below) because
a serverless function cannot read files from the file system at runtime.
"""

import math
from typing import Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Telemetry bundle (embedded; do not read from disk at runtime) ----------
TELEMETRY: List[dict] = [
    # PLACEHOLDER - replaced with the sample telemetry bundle records.
    {"region": "apac", "latency_ms": 100, "uptime": 99.9},
    {"region": "apac", "latency_ms": 200, "uptime": 99.8},
    {"region": "amer", "latency_ms": 150, "uptime": 99.7},
    {"region": "amer", "latency_ms": 170, "uptime": 99.9},
]

app = FastAPI(title="eShopCo latency analytics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: float = 180


def percentile(values: List[float], pct: float) -> float:
    """95th percentile using linear interpolation (numpy.percentile default)."""
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


def metrics_for(records: List[dict], threshold: float) -> dict:
    latencies = [float(r["latency_ms"]) for r in records]
    uptimes = [float(r["uptime"]) for r in records]
    return {
        "avg_latency": (sum(latencies) / len(latencies)) if latencies else 0.0,
        "p95_latency": percentile(latencies, 95),
        "avg_uptime": (sum(uptimes) / len(uptimes)) if uptimes else 0.0,
        "breaches": sum(1 for value in latencies if value > threshold),
    }


def region_records(region: str) -> List[dict]:
    return [r for r in TELEMETRY if str(r.get("region", "")).lower() == region.lower()]


@app.get("/")
def root() -> dict:
    return {"message": "eShopCo latency analytics", "endpoint": "POST /api/latency"}


@app.post("/api/latency")
@app.post("/latency")
@app.post("/")
def latency(payload: LatencyRequest) -> Dict[str, dict]:
    threshold = float(payload.threshold_ms)
    return {
        region: metrics_for(region_records(region), threshold) for region in payload.regions
    }
