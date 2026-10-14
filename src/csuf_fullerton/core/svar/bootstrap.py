"""Residual bootstrap for impulse responses that keeps the block restriction in every draw.

Resample residual vectors jointly (rows), rebuild the series recursively from the first
``p`` observations with the estimated restricted coefficients, re-estimate, recompute IRFs.
Percentile and Hall intervals (Kilian and Lütkepohl 2017, 12.2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from csuf_fullerton.core.svar.data import Array
from csuf_fullerton.core.svar.estimate import VarFit, fit_block_var, fit_var
from csuf_fullerton.core.svar.irf import irf


@dataclass(frozen=True)
class Bands:
    point: Array
    lower: Array
    upper: Array
    draws: int
    level: float
    method: str


def simulate(fit: VarFit, y0: Array, det: Array, shocks: Array) -> Array:
    """Generate ``y`` from the reduced form, with ``y0`` (p x k) as initial values."""
    p = fit.p
    n = shocks.shape[0]
    y = np.zeros((n + p, fit.k))
    y[:p] = y0
    for t in range(p, n + p):
        y[t] = fit.Phi @ det[t] + shocks[t - p]
        for j in range(1, p + 1):
            y[t] += fit.A[j - 1] @ y[t - j]
    return y


def refit(fit: VarFit, y: Array, det: Array) -> VarFit:
    return fit_block_var(y, fit.p, det, fit.nf) if fit.nf else fit_var(y, fit.p, det)


def bootstrap_irf(
    fit: VarFit,
    y: Array,
    det: Array,
    horizon: int,
    draws: int,
    rng: np.random.Generator,
    level: float = 0.68,
    method: str = "percentile",
) -> Bands:
    point = irf(fit, horizon)
    u = fit.resid - fit.resid.mean(axis=0)
    n = u.shape[0]
    out = np.empty((draws, *point.shape))
    for b in range(draws):
        shocks = u[rng.integers(0, n, n)]
        yb = simulate(fit, y[: fit.p], det, shocks)
        out[b] = irf(refit(fit, yb, det), horizon)
    a = (1 - level) / 2
    lo, hi = np.quantile(out, [a, 1 - a], axis=0)
    if method == "hall":
        lo, hi = 2 * point - hi, 2 * point - lo
    return Bands(point, lo, hi, draws, level, method)
