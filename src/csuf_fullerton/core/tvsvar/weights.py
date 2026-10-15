"""Trade weights: partner shares of exports plus imports, smoothed and mapped to months.

Follows Cesa-Bianchi, Pesaran, Rebucci and Xu (2012): the weight of partner ``j`` in year
``y`` is its share of total trade (exports plus imports), averaged over years ``y`` and the
``window - 1`` years before it. With ``lag = 1`` every month of year ``y`` uses the average
ending in ``y - 1``, so the weight is predetermined with respect to that year's shocks.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from csuf_fullerton.core.svar.data import Array


@dataclass(frozen=True)
class TradeWeights:
    """Annual smoothed shares; ``shares[y]`` maps each partner (and ``rest``) to a weight."""

    partners: tuple[str, ...]
    shares: Mapping[int, Mapping[str, float]]
    window: int
    lag: int

    def at(self, year: int) -> Array:
        """Weights of the declared partners in ``year`` (rest of world excluded)."""
        if year not in self.shares:
            raise ValueError(f"no trade weight for {year}")
        return np.array([self.shares[year][p] for p in self.partners])


def annual_shares(
    trade: Mapping[tuple[str, int], float],
    partners: Sequence[str],
    world: str = "world",
    require: Iterable[int] = (),
) -> dict[int, dict[str, float]]:
    """``trade[(partner, year)]`` is exports plus imports; ``world`` holds the total.

    Returns raw (unsmoothed) shares per year with a ``rest`` entry so each year sums to one.
    Years where a partner is missing are left out, except years in ``require`` (the years the
    estimation sample needs), where a gap raises naming the partner and year.
    """
    needed = set(require)
    years = sorted({y for (p, y) in trade if p == world} | needed)
    if not any(p == world for p, _ in trade):
        raise ValueError(f"no '{world}' totals in the trade table")
    out: dict[int, dict[str, float]] = {}
    for y in years:
        gaps = [p for p in (world, *partners) if (p, y) not in trade]
        if gaps:
            if y in needed:
                raise ValueError(f"no trade value for partner '{gaps[0]}' in {y}")
            continue
        total = trade[(world, y)]
        if total <= 0:
            raise ValueError(f"total trade is not positive in {y}")
        row: dict[str, float] = {}
        for p in partners:
            share = trade[(p, y)] / total
            if not 0.0 <= share <= 1.0:
                raise ValueError(f"share of '{p}' in {y} is {share:.3f}, outside [0, 1]")
            row[p] = share
        rest = 1.0 - sum(row.values())
        if rest < -1e-10:
            raise ValueError(f"partner shares exceed one in {y}")
        row["rest"] = max(rest, 0.0)
        out[y] = row
    return out


def smooth(
    raw: Mapping[int, Mapping[str, float]], partners: Sequence[str], window: int = 3, lag: int = 0
) -> TradeWeights:
    """Moving average over ``window`` years ending in ``y - lag``, keyed by ``y``."""
    if window < 1 or lag < 0:
        raise ValueError("window must be at least 1 and lag non-negative")
    years = sorted(raw)
    keys = (*partners, "rest")
    shares: dict[int, dict[str, float]] = {}
    for y in years:
        end = y - lag
        span = list(range(end - window + 1, end + 1))
        if any(s not in raw for s in span):
            continue
        shares[y] = {k: float(np.mean([raw[s][k] for s in span])) for k in keys}
    if not shares:
        raise ValueError("not enough years of trade data for the moving average")
    return TradeWeights(tuple(partners), shares, window, lag)


def monthly(weights: TradeWeights, dates: Sequence[str]) -> Array:
    """T x J matrix of partner weights for ``YYYY-MM`` dates. Gaps raise, never impute."""
    rows = []
    for d in dates:
        y = int(d[:4])
        if y not in weights.shares:
            raise ValueError(
                f"no trade weight for {d}: weights cover {min(weights.shares)}-"
                f"{max(weights.shares)}"
            )
        rows.append(weights.at(y))
    return np.array(rows)


def required_years(dates: Sequence[str], window: int, lag: int) -> range:
    """Years of trade data a sample of ``YYYY-MM`` dates needs for the moving average."""
    first, last = int(dates[0][:4]), int(dates[-1][:4])
    return range(first - lag - window + 1, last - lag + 1)
