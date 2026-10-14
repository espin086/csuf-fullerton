"""Recursive pseudo out-of-sample test of block exogeneity (Clark and West 2007).

The restricted model (foreign block ignores domestic lags) is nested in the unrestricted VAR.
For each foreign variable, one-step forecasts from both are made with expanding-window
estimates. Clark-West adjusted loss difference
``f_t = e_r^2 - (e_u^2 - (yhat_r - yhat_u)^2)``; a significantly positive mean says domestic
variables help forecast the foreign block out of sample, against the restriction.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from csuf_fullerton.core.svar.data import Array
from csuf_fullerton.core.svar.estimate import VarFit, fit_block_var, fit_var


@dataclass(frozen=True)
class ClarkWest:
    variable: str
    stat: float
    pvalue: float  # one-sided, H1: unrestricted forecasts better
    mspe_ratio: float  # unrestricted / restricted MSPE
    nforecasts: int


def one_step(fit: VarFit, y: Array, det_t: Array) -> Array:
    """Forecast of ``y_T`` from ``y`` up to ``T-1``."""
    out = fit.Phi @ det_t
    for j in range(1, fit.p + 1):
        out = out + fit.A[j - 1] @ y[-j]
    return np.asarray(out)


def clark_west_stat(e_r: Array, e_u: Array, f_r: Array, f_u: Array) -> tuple[float, float]:
    f = e_r**2 - (e_u**2 - (f_r - f_u) ** 2)
    n = f.size
    sd = float(f.std(ddof=1))
    t = float(f.mean() / (sd / np.sqrt(n))) if sd > 0 else 0.0
    return t, float(stats.norm.sf(t))


def clark_west(
    names: tuple[str, ...], y: Array, det: Array, p: int, nf: int, start: int
) -> list[ClarkWest]:
    n = y.shape[0]
    if not p + det.shape[1] + y.shape[1] * p < start < n - 5:
        raise ValueError("out-of-sample start leaves too few estimation or forecast points")
    fr, fu, actual = [], [], []
    for t in range(start, n):
        r = fit_block_var(y[:t], p, det[:t], nf)
        u = fit_var(y[:t], p, det[:t])
        fr.append(one_step(r, y[:t], det[t])[:nf])
        fu.append(one_step(u, y[:t], det[t])[:nf])
        actual.append(y[t, :nf])
    a_r, a_u, act = np.array(fr), np.array(fu), np.array(actual)
    out = []
    for i in range(nf):
        e_r, e_u = act[:, i] - a_r[:, i], act[:, i] - a_u[:, i]
        stat, pv = clark_west_stat(e_r, e_u, a_r[:, i], a_u[:, i])
        ratio = float(np.mean(e_u**2) / np.mean(e_r**2))
        out.append(ClarkWest(names[i], stat, pv, ratio, len(act)))
    return out
