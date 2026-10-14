"""Integration order (ADF + KPSS confirmatory pair) and Johansen cointegration rank.

Decision rule per series: I(0) when ADF rejects a unit root at ``alpha`` and KPSS does not
reject stationarity; otherwise test the first difference the same way. ``conflict`` marks
the cases where the two tests agree on neither (both reject or neither rejects).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from scipy import stats
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tsa.vector_ar.vecm import coint_johansen

from csuf_fullerton.core.svar.data import Array


@dataclass(frozen=True)
class OrderResult:
    name: str
    order: int
    adf_p_level: float
    kpss_p_level: float
    adf_p_diff: float
    kpss_p_diff: float
    conflict: bool


def _pair(x: Array, regression: str) -> tuple[float, float]:
    with warnings.catch_warnings():
        # KPSS p-values are interpolated from a table; adfuller warns about its return type
        warnings.simplefilter("ignore")
        adf_p = float(adfuller(x, regression=regression, autolag="AIC")[1])
        kpss_p = float(kpss(x, regression="ct" if regression == "ct" else "c", nlags="auto")[1])
    return adf_p, kpss_p


def integration_order(name: str, x: Array, trend: bool = True, alpha: float = 0.05) -> OrderResult:
    reg = "ct" if trend else "c"
    a0, k0 = _pair(x, reg)
    a1, k1 = _pair(np.diff(x), "c")
    if a0 < alpha and k0 >= alpha:
        return OrderResult(name, 0, a0, k0, a1, k1, False)
    conflict0 = (a0 < alpha) == (k0 < alpha)
    if a1 < alpha and k1 >= alpha:
        return OrderResult(name, 1, a0, k0, a1, k1, conflict0)
    return OrderResult(name, 2, a0, k0, a1, k1, True)


@dataclass(frozen=True)
class JohansenResult:
    rank: int
    trace: tuple[float, ...]
    crit95: tuple[float, ...]
    beta: Array  # k x rank cointegrating vectors


def johansen_rank(y: Array, k_ar_diff: int, trend: bool = True) -> JohansenResult:
    """Trace test, sequential from rank 0, 5% critical values (Johansen 1991), with the
    Reinsel and Ahn (1992) small-sample scaling ``(T - k p) / T`` of the statistic."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = coint_johansen(y, 1 if trend else 0, k_ar_diff)
    t, k = y.shape
    scale = (t - k * (k_ar_diff + 1)) / t
    trace = tuple(float(v) * scale for v in res.lr1)
    crit = tuple(float(v) for v in res.cvt[:, 1])
    rank = 0
    while rank < len(trace) and trace[rank] > crit[rank]:
        rank += 1
    return JohansenResult(rank, trace, crit, np.real(np.asarray(res.evec))[:, :rank])


@dataclass(frozen=True)
class WeakExogeneity:
    name: str
    stat: float  # F statistic
    df1: int
    df2: int
    pvalue: float


def weak_exogeneity(
    names: tuple[str, ...],
    y: Array,
    det: Array,
    beta: Array,
    beta_foreign: Array,
    p: int,
    targets: list[int],
) -> list[WeakExogeneity]:
    """Weak exogeneity of foreign variables for the domestic long-run relations.

    Following the GVAR tests of Pesaran, Schuermann and Weiner (2004): regress ``Δy_i,t`` on
    deterministic terms, ``p - 1`` lagged differences (at least one) and the foreign-only
    error-correction terms ``beta_foreign' y_{t-1}``; F-test whether adding the full-system
    terms ``beta' y_{t-1}`` helps. A cointegrating relation among foreign variables alone is
    allowed (it does not involve the domestic economy); a rejection means variable ``i``
    adjusts to disequilibria that involve domestic variables, so it is not weakly exogenous.
    ``beta_foreign`` is k x r_f with zero rows for domestic variables.
    """
    if beta.shape[1] == 0:
        return []
    dy = np.diff(y, axis=0)
    q = max(p - 1, 1)
    lags = np.hstack([dy[q - j : dy.shape[0] - j] for j in range(1, q + 1)])
    lhs = dy[q:]
    d = det[1:][q:]
    x_r = np.hstack([d, lags, (y[:-1] @ beta_foreign)[q:]])
    x_u = np.hstack([x_r, (y[:-1] @ beta)[q:]])
    df1 = int(np.linalg.matrix_rank(x_u) - np.linalg.matrix_rank(x_r))
    n = lhs.shape[0]
    df2 = n - int(np.linalg.matrix_rank(x_u))
    out = []
    for i in targets:
        if df1 <= 0:
            out.append(WeakExogeneity(names[i], 0.0, 0, df2, 1.0))
            continue
        rss = []
        for x in (x_r, x_u):
            coef = np.linalg.lstsq(x, lhs[:, i], rcond=None)[0]
            rss.append(float(np.sum((lhs[:, i] - x @ coef) ** 2)))
        f = ((rss[0] - rss[1]) / df1) / (rss[1] / df2)
        out.append(WeakExogeneity(names[i], f, df1, df2, float(stats.f.sf(f, df1, df2))))
    return out
