"""Data containers, deterministic terms and lag matrices. Pure functions over arrays."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]


@dataclass(frozen=True)
class Dataset:
    """Aligned sample: ``values`` is T x k, ``season`` is the period-of-year code per row
    (1..12 for monthly, 1..4 for quarterly) or None."""

    names: tuple[str, ...]
    values: Array
    dates: tuple[str, ...]
    season: NDArray[np.int64] | None = None
    period: int = 12

    def select(self, names: Sequence[str]) -> Dataset:
        idx = [self.names.index(n) for n in names]
        return Dataset(tuple(names), self.values[:, idx], self.dates, self.season, self.period)

    @property
    def nobs(self) -> int:
        return int(self.values.shape[0])


def make_dataset(
    names: Sequence[str],
    values: Array,
    dates: Sequence[str],
    season: Sequence[int] | None = None,
    period: int = 12,
) -> Dataset:
    """Validate shapes and drop rows with any missing value (keeps the longest clean block
    at the end of the sample so the series stay contiguous)."""
    vals = np.asarray(values, dtype=float)
    if vals.ndim != 2 or vals.shape[1] != len(names):
        raise ValueError("values must be T x k with one column per name")
    if len(set(names)) != len(names):
        raise ValueError("duplicate column names")
    ok = np.all(np.isfinite(vals), axis=1)
    if not ok.any():
        raise ValueError("no complete rows")
    # last contiguous run of complete rows
    end = int(np.flatnonzero(ok)[-1]) + 1
    start = end
    while start > 0 and ok[start - 1]:
        start -= 1
    seas = None if season is None else np.asarray(season, dtype=np.int64)[start:end]
    return Dataset(tuple(names), vals[start:end], tuple(dates[start:end]), seas, period)


def deterministic(
    nobs: int,
    trend: bool = False,
    season: NDArray[np.int64] | None = None,
    period: int = 12,
) -> Array:
    """Constant, optional linear trend, optional centred seasonal dummies (period - 1 columns)."""
    cols = [np.ones(nobs)]
    if trend:
        cols.append(np.arange(1, nobs + 1, dtype=float))
    if season is not None:
        for s in range(2, period + 1):
            d = (season == s).astype(float)
            cols.append(d - 1.0 / period)
    return np.column_stack(cols)


def lag_matrix(y: Array, p: int) -> Array:
    """Rows t = p..T-1 of [y_{t-1}, ..., y_{t-p}] (lag-major blocks of k columns)."""
    t, _ = y.shape
    if p < 1:
        return np.empty((t, 0))
    return np.hstack([y[p - lag : t - lag] for lag in range(1, p + 1)])
