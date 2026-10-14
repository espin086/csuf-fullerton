"""Build replication/fixtures/primiceri_us.csv from FRED (keyless), as in Primiceri (2005).

Inflation is the annualised quarterly growth of the GDP deflator, unemployment the quarterly
average civilian unemployment rate, the interest rate the quarterly average 3-month T-bill
rate. Sample 1953Q1 to 2001Q3 (the paper's). Run from the repo root:

    .venv/bin/python replication/scripts/make_primiceri_fixture.py
"""

from __future__ import annotations

import csv
import itertools
import math
from collections import defaultdict
from pathlib import Path

from csuf_fullerton.data.adapters import fred

OUT = Path("replication/fixtures/primiceri_us.csv")


def quarterly_mean(obs: dict[str, float]) -> dict[str, float]:
    acc: dict[str, list[float]] = defaultdict(list)
    for d, v in obs.items():
        acc[f"{d[:4]}Q{(int(d[5:7]) - 1) // 3 + 1}"].append(v)
    return {q: sum(v) / len(v) for q, v in acc.items() if len(v) == 3}


def main() -> None:
    defl = {
        f"{d[:4]}Q{(int(d[5:7]) - 1) // 3 + 1}": v
        for d, v in fred.fetch_series("GDPDEF", None).items()
    }
    unr = quarterly_mean(fred.fetch_series("UNRATE", None))
    tb = quarterly_mean(fred.fetch_series("TB3MS", None))
    quarters = sorted(defl)
    rows = []
    for prev, q in itertools.pairwise(quarters):
        if not ("1953Q1" <= q <= "2001Q3") or q not in unr or q not in tb:
            continue
        infl = 400 * math.log(defl[q] / defl[prev])
        rows.append([q, round(infl, 6), round(unr[q], 6), round(tb[q], 6)])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "inflation", "unemployment", "tbill"])
        w.writerows(rows)
    print(f"wrote {OUT} ({len(rows)} quarters)")


if __name__ == "__main__":
    main()
