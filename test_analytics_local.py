"""Local checks for POST /analytics (auth, CORS, aggregation).

Usage: python test_analytics_local.py [base_url]   (default http://127.0.0.1:8777)
"""

import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from decimal import Decimal

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8777"
KEY = "ak_h609yeskd3fjyeyppukt11vx"
EMAIL = "24f2005949@ds.study.iitm.ac.in"

failures = []


def post(path, body=None, headers=None, method="POST"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json",
                                          **(headers or {})})
    def norm(mapping):
        # uvicorn emits lower-cased header names; keep lookups case-insensitive
        return {key.lower(): value for key, value in mapping.items()}

    try:
        # 45s: the first call after a fresh deploy can hit a cold serverless start
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read()
            try:
                parsed = json.loads(raw) if raw.strip() else {}
            except ValueError:
                parsed = {"raw": raw.decode(errors="replace")}
            return resp.status, norm(resp.headers), parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw or b"{}")
        except ValueError:
            parsed = {"raw": raw.decode(errors="replace")}
        return exc.code, norm(exc.headers), parsed


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + ("  " + detail if detail else ""))
    if not ok:
        failures.append(label)


# 1. missing API key -> 401
status, _, _ = post("/analytics", {"events": []})
check("missing key -> 401", status == 401, f"got {status}")

# 2. wrong API key -> 401
status, _, _ = post("/analytics", {"events": []}, {"X-API-Key": "ak_wrong_key_value"})
check("wrong key -> 401", status == 401, f"got {status}")

# 3. empty-ish valid batch still authenticates
status, _, body = post("/analytics", {"events": []}, {"X-API-Key": KEY})
check("valid key + empty batch -> 200", status == 200, f"got {status} {body}")

# 4. fresh randomized-style batch: 12 events, 5 users, mixed amounts
events = [
    {"user": "alice", "amount": 42.5, "ts": 1700000000},
    {"user": "bob", "amount": 100, "ts": 1700000001},
    {"user": "alice", "amount": -10, "ts": 1700000002},
    {"user": "carol", "amount": -5, "ts": 1700000003},
    {"user": "dave", "amount": 0.01, "ts": 1700000004},
    {"user": "bob", "amount": 0, "ts": 1700000005},
    {"user": "erin", "amount": -100, "ts": 1700000006},
    {"user": "alice", "amount": 7.25, "ts": 1700000007},
    {"user": "dave", "amount": 60, "ts": 1700000008},
    {"user": "carol", "amount": 3.33, "ts": 1700000009},
    {"user": "erin", "amount": 20, "ts": 1700000010},
    {"user": "bob", "amount": 50, "ts": 1700000011},
]
status, _, body = post("/analytics", {"events": events}, {"X-API-Key": KEY})
check("valid key + batch -> 200", status == 200, f"got {status}")

# independent expectation (Decimal money maths, Counter for users)
users = Counter(e["user"] for e in events)
revenue = sum((Decimal(str(e["amount"])) for e in events if e["amount"] > 0), Decimal(0))
positive_totals = Counter()
for e in events:
    if e["amount"] > 0:
        positive_totals[e["user"]] += Decimal(str(e["amount"]))
expected = {
    "email": EMAIL,
    "total_events": len(events),
    "unique_users": len(users),
    "revenue": float(revenue),
    "top_user": positive_totals.most_common(1)[0][0],
}

if status == 200:
    check("email", body.get("email") == expected["email"], str(body.get("email")))
    check("total_events", body.get("total_events") == expected["total_events"],
          f"got {body.get('total_events')} want {expected['total_events']}")
    check("unique_users", body.get("unique_users") == expected["unique_users"],
          f"got {body.get('unique_users')} want {expected['unique_users']}")
    check("revenue", abs(float(body.get("revenue", -1)) - expected["revenue"]) < 1e-6,
          f"got {body.get('revenue')} want {expected['revenue']}")
    check("top_user", body.get("top_user") == expected["top_user"],
          f"got {body.get('top_user')} want {expected['top_user']}")
    check("response keys exact", set(body) == set(expected), str(sorted(body)))

# 5. CORS preflight (browser sends this before the POST)
status, headers, _ = post("/analytics", None,
                          {"Origin": "https://example.com",
                           "Access-Control-Request-Method": "POST",
                           "Access-Control-Request-Headers": "x-api-key,content-type"},
                          method="OPTIONS")
acao = headers.get("access-control-allow-origin", "")
check("preflight 2xx", 200 <= status < 300, f"got {status}")
check("preflight ACAO *", acao in ("*", "https://example.com"), f"got {acao!r}")
check("preflight allows x-api-key",
      "x-api-key" in headers.get("access-control-allow-headers", "").lower(),
      headers.get("access-control-allow-headers", ""))

# 6. CORS on the actual POST response
status, headers, _ = post("/analytics", {"events": events},
                          {"X-API-Key": KEY, "Origin": "https://example.com"})
check("POST ACAO *",
      headers.get("access-control-allow-origin") in ("*", "https://example.com"),
      str(headers.get("access-control-allow-origin")))

# 7. a second, different batch must produce different numbers (no hard-coding)
batch2 = [{"user": "zoe", "amount": 5, "ts": 1}, {"user": "zoe", "amount": 6, "ts": 2},
          {"user": "max", "amount": -3, "ts": 3}]
status, _, body2 = post("/analytics", {"events": batch2}, {"X-API-Key": KEY})
check("second batch recomputed",
      status == 200 and body2.get("total_events") == 3 and body2.get("unique_users") == 2
      and abs(body2.get("revenue", 0) - 11) < 1e-9 and body2.get("top_user") == "zoe",
      str(body2))

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("ALL CHECKS PASSED")
