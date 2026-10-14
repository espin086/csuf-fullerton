"""IMF SDMX 3.0 driver (api.imf.org, no key). One dataflow query per series, CSV format."""

from __future__ import annotations

import csv
import io
import urllib.parse
import urllib.request
from collections.abc import Mapping

BASE = "https://api.imf.org/external/sdmx/3.0/data/dataflow"
ACCEPT = "application/vnd.sdmx.data+csv;version=2.0.0"
TIMEOUT = 120


def _period_to_date(period: str) -> str:
    """'2005-M01' -> '2005-01-01'; '2005-Q2' -> '2005-04-01'; '2005' -> '2005-01-01'."""
    if "-M" in period:
        y, m = period.split("-M")
        return f"{y}-{int(m):02d}-01"
    if "-Q" in period:
        y, q = period.split("-Q")
        return f"{y}-{3 * int(q) - 2:02d}-01"
    return f"{period[:4]}-01-01"


def select_series(
    rows: list[dict[str, str]], filters: Mapping[str, str], label: str
) -> dict[str, float]:
    """Keep rows that match every filter; fail if more than one series remains."""
    keep = [
        r for r in rows if all(r.get(k) == v for k, v in filters.items()) and r.get("OBS_VALUE")
    ]
    if not keep:
        raise ValueError(f"{label}: no IMF observations match {dict(filters)}")
    out: dict[str, float] = {}
    for r in keep:
        d = _period_to_date(r["TIME_PERIOD"])
        if d in out:
            dims = sorted(k for k in r if k not in filters and len({x.get(k) for x in keep}) > 1)
            raise ValueError(f"{label}: filters match several series; add one of {dims}")
        out[d] = float(r["OBS_VALUE"])
    return out


def fetch_rows(
    dataflow: str, filters: Mapping[str, str], agency: str = "IMF.STA"
) -> list[dict[str, str]]:
    """All rows of a dataflow for the COUNTRY and FREQUENCY in ``filters``."""
    query = {f"c[{k}]": v for k, v in filters.items() if k in ("COUNTRY", "FREQUENCY")}
    url = f"{BASE}/{agency}/{dataflow}/+/*?{urllib.parse.urlencode(query)}"
    headers = {"Accept": ACCEPT, "User-Agent": "csuf-fullerton"}
    req = urllib.request.Request(url, headers=headers)  # noqa: S310
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310
        text = resp.read().decode()
    return list(csv.DictReader(io.StringIO(text)))


def fetch_series(
    dataflow: str, filters: Mapping[str, str], agency: str = "IMF.STA"
) -> dict[str, float]:
    return select_series(fetch_rows(dataflow, filters, agency), filters, f"{agency}/{dataflow}")


TRADE_FLOWS = ("XG_FOB_USD", "MG_CIF_USD")  # goods exports FOB and imports CIF, U.S. dollars


def trade_table(
    rows: list[dict[str, str]], partners: Mapping[str, str], world: str = "G001"
) -> dict[tuple[str, int], float]:
    """Annual exports plus imports by partner name from IMTS rows; ``world`` keys the total.

    ``partners`` maps a short name (``us``) to an IMF counterpart code (``USA``). A year is
    kept only when both flows are present for that counterpart.
    """
    codes = {**{v: k for k, v in partners.items()}, world: "world"}
    flows: dict[tuple[str, int], dict[str, float]] = {}
    for r in rows:
        if r.get("INDICATOR") not in TRADE_FLOWS or not r.get("OBS_VALUE"):
            continue
        name = codes.get(r.get("COUNTERPART_COUNTRY", ""))
        if name is None:
            continue
        key = (name, int(r["TIME_PERIOD"][:4]))
        flows.setdefault(key, {})[r["INDICATOR"]] = float(r["OBS_VALUE"])
    return {k: sum(v.values()) for k, v in flows.items() if len(v) == len(TRADE_FLOWS)}
