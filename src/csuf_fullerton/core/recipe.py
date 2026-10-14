"""Data recipe: which series to fetch, how to transform them, and how to align them.

Pure: parsing a TOML mapping and assembling already-fetched observations. Fetching lives in
``csuf_fullerton.data``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

TRANSFORMS = ("level", "log", "log100")
SOURCES = ("fred", "imf")


@dataclass(frozen=True)
class SeriesSpec:
    name: str
    source: str
    series_id: str = ""  # FRED id
    dataflow: str = ""  # IMF dataflow
    filters: Mapping[str, str] = field(default_factory=dict)
    transform: str = "level"
    scale: float = 1.0
    description: str = ""


@dataclass(frozen=True)
class Recipe:
    frequency: str
    start: str
    end: str
    series: tuple[SeriesSpec, ...]


def parse_recipe(doc: Mapping[str, Any]) -> Recipe:
    meta = doc.get("meta", {})
    freq = str(meta.get("frequency", "M")).upper()
    if freq != "M":
        raise ValueError("only monthly recipes are supported")
    out = []
    for s in doc.get("series", []):
        if s.get("source") not in SOURCES:
            raise ValueError(f"series {s.get('name')!r}: source must be one of {SOURCES}")
        if s.get("transform", "level") not in TRANSFORMS:
            raise ValueError(f"series {s.get('name')!r}: transform must be one of {TRANSFORMS}")
        out.append(
            SeriesSpec(
                name=s["name"],
                source=s["source"],
                series_id=s.get("id", ""),
                dataflow=s.get("dataflow", ""),
                filters=dict(s.get("filters", {})),
                transform=s.get("transform", "level"),
                scale=float(s.get("scale", 1.0)),
                description=s.get("description", ""),
            )
        )
    names = [s.name for s in out]
    if not out or len(set(names)) != len(names):
        raise ValueError("recipe needs uniquely named series")
    return Recipe(freq, str(meta.get("start", "")), str(meta.get("end", "")), tuple(out))


def transform_value(x: float, how: str, scale: float = 1.0) -> float:
    v = x * scale
    if how == "level":
        return v
    if v <= 0:
        return math.nan
    return math.log(v) if how == "log" else 100.0 * math.log(v)


def month_range(start: str, end: str) -> list[str]:
    y, m = int(start[:4]), int(start[5:7])
    ye, me = int(end[:4]), int(end[5:7])
    out = []
    while (y, m) <= (ye, me):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def assemble(
    recipe: Recipe, raw: Mapping[str, Mapping[str, float]]
) -> tuple[list[str], list[list[float]]]:
    """Align fetched {date: value} maps on a monthly index (YYYY-MM), transformed.
    The index runs from the recipe start (or the earliest observation) to the end."""
    monthly = {s.name: {d[:7]: v for d, v in raw[s.name].items()} for s in recipe.series}
    all_months = sorted({m for series in monthly.values() for m in series})
    start = recipe.start or all_months[0]
    end = recipe.end or all_months[-1]
    dates = month_range(start, end)
    rows = []
    for d in dates:
        row = []
        for s in recipe.series:
            v = monthly[s.name].get(d)
            row.append(math.nan if v is None else transform_value(v, s.transform, s.scale))
        rows.append(row)
    return dates, rows
