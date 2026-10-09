"""Regenerate the embedded telemetry in api/index.py from a q-vercel-latency.json file.

Usage:  python update_data.py <path-to-q-vercel-latency.json>
"""

import json
import re
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).parent
API_DIR = PROJECT / "api"
INDEX = API_DIR / "index.py"

BLOCK = re.compile(
    r"EMBEDDED_TELEMETRY: List\[dict\] = \[.*?\n\]",
    re.DOTALL,
)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    src = Path(sys.argv[1])
    records = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise SystemExit("Expected a non-empty JSON list of records")

    # 1. ship the file next to index.py (readable at import time)
    API_DIR.mkdir(parents=True, exist_ok=True)
    (API_DIR / "q-vercel-latency.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )

    # 2. embed the records as a Python literal (guaranteed to ship in the bundle)
    body = json.dumps(records, indent=4)
    block = f"EMBEDDED_TELEMETRY: List[dict] = {body}"
    source = INDEX.read_text(encoding="utf-8")
    if not BLOCK.search(source):
        raise SystemExit("Could not locate EMBEDDED_TELEMETRY block in api/index.py")
    INDEX.write_text(BLOCK.sub(lambda m: block, source, count=1), encoding="utf-8")

    regions = sorted({str(r.get("region")) for r in records})
    print(f"Embedded {len(records)} records for regions {regions} into {INDEX}")
    print(f"Also wrote {(API_DIR / 'q-vercel-latency.json')}")


if __name__ == "__main__":
    main()
