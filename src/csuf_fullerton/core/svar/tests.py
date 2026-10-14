"""Hypothesis tests and selection criteria for (block-restricted) VARs.

References: Lütkepohl (2005) sections 3.6 (Granger and instantaneous causality), 4.3 (order
selection) and 4.4 (portmanteau); Sims (1980) small-sample LR correction; Toda and Yamamoto
(1995) lag augmentation for possibly integrated series.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats

from csuf_fullerton.core.svar.data import Array
from csuf_fullerton.core.svar.estimate import VarFit, fit_block_var, fit_var


@dataclass(frozen=True)
class TestStat:
    name: str
    stat: float
    df: int
    pvalue: float


def _logdet(m: Array) -> float:
    sign, val = np.linalg.slogdet(m)
    if sign <= 0:
        raise ValueError("covariance matrix is not positive definite")
    return float(val)


def lr_block_exogeneity(y: Array, p: int, det: Array, nf: int) -> TestStat:
    """``LR = (T - c)(ln|S_r| - ln|S_u|)``, c = parameters per unrestricted equation,
    df = nf * nd * p. Same sample and lags for both fits."""
    u = fit_var(y, p, det)
    r = fit_block_var(y, p, det, nf)
    c = det.shape[1] + y.shape[1] * p
    stat = (u.nobs - c) * (_logdet(r.sigma) - _logdet(u.sigma))
    df = nf * (y.shape[1] - nf) * p
    return TestStat("block exogeneity LR (Sims)", stat, df, float(stats.chi2.sf(stat, df)))


def wald_zero(fit: VarFit, equations: Sequence[int], regressors: Sequence[int]) -> TestStat:
    """Wald test that ``coef[regressors, equations] = 0`` in an unrestricted VAR fit.

    ``Cov(vec B) = Sigma_u ⊗ (X'X)^{-1}`` with the degrees-of-freedom-adjusted ``Sigma_u``.
    """
    if fit.nf:
        raise ValueError("Wald test needs the unrestricted fit")
    x = fit.X
    n, m = x.shape
    sig = fit.resid.T @ fit.resid / (n - m)
    xtx_inv = np.linalg.inv(x.T @ x)
    b = fit.coef
    eq = list(equations)
    rg = list(regressors)
    theta = np.array([b[r, e] for e in eq for r in rg])
    cov = np.kron(sig[np.ix_(eq, eq)], xtx_inv[np.ix_(rg, rg)])
    stat = float(theta @ np.linalg.solve(cov, theta))
    df = theta.size
    return TestStat("Wald", stat, df, float(stats.chi2.sf(stat, df)))


def lag_regressor_index(k: int, m: int, variables: Sequence[int], lags: Sequence[int]) -> list[int]:
    """Column positions of ``variables`` at ``lags`` (1-based) in ``[d_t, y_{t-1}, ...]``."""
    return [m + (lag - 1) * k + v for lag in lags for v in variables]


def lag_augmented_wald(
    y: Array,
    p: int,
    dmax: int,
    det: Array,
    cause: Sequence[int],
    effect: Sequence[int],
) -> TestStat:
    """Toda-Yamamoto: fit VAR(p + dmax), test the first ``p`` lags of ``cause`` in the
    ``effect`` equations. Chi-square with ``len(cause) * len(effect) * p`` df regardless of
    the integration or cointegration properties."""
    fit = fit_var(y, p + dmax, det)
    idx = lag_regressor_index(y.shape[1], det.shape[1], cause, range(1, p + 1))
    res = wald_zero(fit, effect, idx)
    return TestStat(f"lag-augmented Wald (p={p}, d_max={dmax})", res.stat, res.df, res.pvalue)


def instantaneous_block(resid: Array, nf: int) -> TestStat:
    """LR test that residual blocks are uncorrelated:
    ``T (ln|S_FF| + ln|S_DD| - ln|S|)``, df nf * nd."""
    n, k = resid.shape
    s = resid.T @ resid / n
    stat = n * (_logdet(s[:nf, :nf]) + _logdet(s[nf:, nf:]) - _logdet(s))
    df = nf * (k - nf)
    return TestStat("block instantaneous causality", stat, df, float(stats.chi2.sf(stat, df)))


def instantaneous_pair(resid: Array, i: int, j: int) -> TestStat:
    n = resid.shape[0]
    r = float(np.corrcoef(resid[:, i], resid[:, j])[0, 1])
    stat = n * r * r
    return TestStat("instantaneous causality", stat, 1, float(stats.chi2.sf(stat, 1)))


@dataclass(frozen=True)
class Criteria:
    aic: float
    bic: float
    hq: float


def criteria(fit: VarFit) -> Criteria:
    """Lütkepohl (2005) 4.3: ``ln|Sigma| + penalty * n / T`` with n free parameters."""
    ld = _logdet(fit.sigma)
    n, t = fit.nparams, fit.nobs
    return Criteria(ld + 2 * n / t, ld + n * np.log(t) / t, ld + 2 * n * np.log(np.log(t)) / t)


def select_lags(y: Array, max_lags: int, det: Array) -> dict[str, int]:
    """AIC, BIC and HQ choices on a common sample (first ``max_lags`` rows held back)."""
    best: dict[str, tuple[float, int]] = {}
    for p in range(1, max_lags + 1):
        fit = fit_var(y[max_lags - p :], p, det[max_lags - p :])
        c = criteria(fit)
        for name, val in (("aic", c.aic), ("bic", c.bic), ("hq", c.hq)):
            if name not in best or val < best[name][0]:
                best[name] = (val, p)
    return {name: v[1] for name, v in best.items()}


def portmanteau(fit: VarFit, h: int = 12) -> TestStat:
    """Adjusted portmanteau ``T^2 sum_j tr(C_j' C_0^{-1} C_j C_0^{-1}) / (T - j)``,
    df ``k^2 (h - p)``."""
    u = fit.resid - fit.resid.mean(axis=0)
    n, k = u.shape
    c0inv = np.linalg.inv(u.T @ u / n)
    q = 0.0
    for j in range(1, h + 1):
        cj = u[j:].T @ u[:-j] / n
        q += float(np.trace(cj.T @ c0inv @ cj @ c0inv)) / (n - j)
    stat = n * n * q
    df = k * k * max(h - fit.p, 1)
    return TestStat(f"portmanteau (h={h})", stat, df, float(stats.chi2.sf(stat, df)))


def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm (1979) step-down adjusted p-values, same order as the input."""
    p = np.asarray(pvalues, dtype=float)
    m = p.size
    order = np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj.tolist()


def bootstrap_block_wald(
    y: Array,
    p: int,
    dmax: int,
    det: Array,
    foreign: Sequence[int],
    draws: int,
    rng: np.random.Generator,
) -> TestStat:
    """Lag-augmented block Wald with a residual-bootstrap p-value (Hacker and Hatemi-J 2006).

    Data are regenerated from the block-exogenous VAR(p + dmax), which satisfies the null,
    using recentred residuals; ``p = (1 + #{W* >= W}) / (B + 1)``. Corrects the small-sample
    over-rejection of the asymptotic chi-square test.
    """
    from csuf_fullerton.core.svar.bootstrap import simulate

    k = y.shape[1]
    f = list(foreign)
    d = [i for i in range(k) if i not in f]
    observed = lag_augmented_wald(y, p, dmax, det, d, f)
    order = f + d
    back = np.argsort(order)
    null = fit_block_var(y[:, order], p + dmax, det, len(f))
    u = null.resid - null.resid.mean(axis=0)
    n = u.shape[0]
    exceed = 0
    for _ in range(draws):
        yb = simulate(null, y[: p + dmax, order], det, u[rng.integers(0, n, n)])[:, back]
        if lag_augmented_wald(yb, p, dmax, det, d, f).stat >= observed.stat:
            exceed += 1
    pval = (1 + exceed) / (draws + 1)
    return TestStat(f"{observed.name}, bootstrap {draws}", observed.stat, observed.df, pval)
