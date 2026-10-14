"""M0: the constant block-exogenous SVAR as a baseline, with tests of parameter stability.

Stability is tested on the domestic block, which is where foreign-shock transmission lives:
``z_t`` on deterministic terms, current ``x_t`` and ``p`` lags of every variable (the 0002
domestic regression). Two tests:

* Chow-type LR at a researcher-chosen break date.
* Andrews (1993) sup-LR over every break date in the middle ``1 - 2 * trim`` of the sample.

Both use a residual-bootstrap p-value under the constant model (the asymptotic sup-LR
distribution depends on the number of parameters and the trimming, and the chi-square
approximation for the Chow test is poor with this many regressors).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from csuf_fullerton.core.svar.bootstrap import simulate
from csuf_fullerton.core.svar.data import Array, lag_matrix
from csuf_fullerton.core.svar.estimate import VarFit, fit_block_var


def domestic_design(y: Array, p: int, det: Array, nf: int) -> tuple[Array, Array]:
    """Regressors and left-hand side of the 0002 domestic regression, rows ``t = p..T-1``."""
    x = np.hstack([det[p:], y[p:, :nf], lag_matrix(y, p)])
    return x, y[p:, nf:]


def _ssr_logdet(x: Array, z: Array) -> float:
    beta, *_ = np.linalg.lstsq(x, z, rcond=None)
    u = z - x @ beta
    sign, val = np.linalg.slogdet(u.T @ u / len(z))
    if sign <= 0:
        raise ValueError("residual covariance is not positive definite")
    return float(val)


def _split_lr(x: Array, z: Array, b: int) -> float:
    """``n (ln|S_full| - ln|S_split|)`` with ``S_split`` the pooled two-regime covariance."""
    n = len(z)
    beta1, *_ = np.linalg.lstsq(x[:b], z[:b], rcond=None)
    beta2, *_ = np.linalg.lstsq(x[b:], z[b:], rcond=None)
    u = np.vstack([z[:b] - x[:b] @ beta1, z[b:] - x[b:] @ beta2])
    sign, val = np.linalg.slogdet(u.T @ u / n)
    if sign <= 0:
        raise ValueError("split residual covariance is not positive definite")
    return n * (_ssr_logdet(x, z) - float(val))


@dataclass(frozen=True)
class BreakTest:
    name: str
    stat: float
    df: int
    asymptotic_p: float | None
    bootstrap_p: float
    break_index: int  # row of the effective sample where the second regime starts
    draws: int


def _sup(x: Array, z: Array, lo: int, hi: int) -> tuple[float, int]:
    best, arg = -np.inf, lo
    for b in range(lo, hi + 1):
        s = _split_lr(x, z, b)
        if s > best:
            best, arg = s, b
    return float(best), arg


def _bounds(n: int, q: int, trim: float) -> tuple[int, int]:
    lo = max(int(np.ceil(trim * n)), q + 1)
    hi = min(int(np.floor((1 - trim) * n)), n - q - 1)
    if lo > hi:
        raise ValueError("sample too short for the break test at this trimming")
    return lo, hi


def stability_tests(
    y: Array,
    p: int,
    det: Array,
    nf: int,
    break_index: int | None,
    rng: np.random.Generator,
    draws: int = 199,
    trim: float = 0.15,
) -> list[BreakTest]:
    """Chow LR at ``break_index`` (effective-sample row, if given) and sup-LR, with bootstrap
    p-values from the constant 0002 fit."""
    x, z = domestic_design(y, p, det, nf)
    n, q = x.shape
    df = q * z.shape[1]
    lo, hi = _bounds(n, q, trim)
    sup_stat, sup_arg = _sup(x, z, lo, hi)
    chow = None
    if break_index is not None:
        if not q < break_index < n - q:
            raise ValueError("break date leaves too few observations in one regime")
        chow = _split_lr(x, z, break_index)
    fit = fit_block_var(y, p, det, nf)
    u = fit.resid - fit.resid.mean(axis=0)
    sup_draws = np.empty(draws)
    chow_draws = np.empty(draws)
    for i in range(draws):
        ys = simulate(fit, y[:p], det, u[rng.integers(0, n, n)])
        xs, zs = domestic_design(ys, p, det, nf)
        sup_draws[i] = _sup(xs, zs, lo, hi)[0]
        if chow is not None and break_index is not None:
            chow_draws[i] = _split_lr(xs, zs, break_index)
    out = [
        BreakTest(
            "sup-LR (Andrews 1993), domestic block",
            sup_stat,
            df,
            None,
            float((1 + np.sum(sup_draws >= sup_stat)) / (draws + 1)),
            sup_arg,
            draws,
        )
    ]
    if chow is not None and break_index is not None:
        out.insert(
            0,
            BreakTest(
                "Chow LR at the chosen date, domestic block",
                chow,
                df,
                float(stats.chi2.sf(chow, df)),
                float((1 + np.sum(chow_draws >= chow)) / (draws + 1)),
                break_index,
                draws,
            ),
        )
    return out


def split_fits(y: Array, p: int, det: Array, nf: int, break_row: int) -> tuple[VarFit, VarFit]:
    """0002 fits on each side of ``break_row`` (a row of ``y``); the second keeps ``p`` rows of
    pre-break history as initial values."""
    return (
        fit_block_var(y[:break_row], p, det[:break_row], nf),
        fit_block_var(y[break_row - p :], p, det[break_row - p :], nf),
    )
