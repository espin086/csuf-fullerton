"""Compare a regenerated output tree with the committed one, numerically.

    .venv/bin/python scripts/compare_outputs.py reports/nicaragua/outputs results/nicaragua

Every CSV present in both trees must have the same shape and columns, identical text columns
and numeric columns equal within --tol (default 1e-8). Markdown reports must match after
dropping lines that carry run timestamps. Images and run.json timestamps are not compared.
Exit code 1 on any difference.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def compare_csv(a: Path, b: Path, tol: float) -> list[str]:
    da, db = pd.read_csv(a), pd.read_csv(b)
    if list(da.columns) != list(db.columns) or da.shape != db.shape:
        return [f"{a.name}: shape or columns differ ({da.shape} vs {db.shape})"]
    out = []
    for c in da.columns:
        if pd.api.types.is_numeric_dtype(da[c]) and pd.api.types.is_numeric_dtype(db[c]):
            x, y = da[c].to_numpy(float), db[c].to_numpy(float)
            both_nan = np.isnan(x) & np.isnan(y)
            diff = np.where(both_nan, 0.0, np.abs(x - y))
            if np.nanmax(diff, initial=0.0) > tol or np.any(np.isnan(x) != np.isnan(y)):
                out.append(f"{a.name}:{c} max abs diff {np.nanmax(diff):.3g}")
        elif not da[c].astype(str).equals(db[c].astype(str)):
            out.append(f"{a.name}:{c} text differs")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("committed", type=Path)
    ap.add_argument("regenerated", type=Path)
    ap.add_argument("--tol", type=float, default=1e-8)
    args = ap.parse_args()
    problems: list[str] = []
    compared = 0
    for f in sorted(args.committed.rglob("*")):
        rel = f.relative_to(args.committed)
        g = args.regenerated / rel
        if f.suffix not in (".csv", ".md"):
            continue
        if not g.exists():
            problems.append(f"{rel}: missing from regenerated tree")
            continue
        compared += 1
        if f.suffix == ".csv":
            problems += [f"{rel.parent}/{p}" for p in compare_csv(f, g, args.tol)]
        elif f.read_text() != g.read_text():
            problems.append(f"{rel}: report text differs")
    for p in problems:
        print(f"DIFF  {p}")
    print(f"{compared} files compared, {len(problems)} differences.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
