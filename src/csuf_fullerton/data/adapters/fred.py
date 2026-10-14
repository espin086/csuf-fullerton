"""FRED driver: the official API when a key is available, the keyless fredgraph CSV otherwise."""

from __future__ import annotations

import csv
import io
import json
import urllib.parse
import urllib.request

API = "https://api.stlouisfed.org/fred/series/observations"
GRAPH = "https://fred.stlouisfed.org/graph/fredgraph.csv"
TIMEOUT = 60


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "csuf-fullerton"})  # noqa: S310
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310
        return bytes(resp.read())


def fetch_series(
    series_id: str, api_key: str | None, frequency: str | None = None
) -> dict[str, float]:
    """Return {YYYY-MM-DD: value}; missing observations ('.') are dropped."""
    if api_key:
        params = {"series_id": series_id, "api_key": api_key, "file_type": "json"}
        if frequency:
            params |= {"frequency": frequency.lower(), "aggregation_method": "avg"}
        body = json.loads(_get(f"{API}?{urllib.parse.urlencode(params)}"))
        rows = [(o["date"], o["value"]) for o in body["observations"]]
    else:
        text = _get(f"{GRAPH}?{urllib.parse.urlencode({'id': series_id})}").decode()
        reader = csv.reader(io.StringIO(text))
        next(reader)
        rows = [(r[0], r[1]) for r in reader if len(r) >= 2]
    return {d: float(v) for d, v in rows if v not in (".", "")}
