"""Data-generating processes with known answers, used by the tests and the replication suite.

Each DGP returns the simulated data and enough of the truth to score an estimator.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from csuf_fullerton.core.svar.data import Array
from csuf_fullerton.core.svar.irf import ma_coefficients

# M1 DGP: foreign block (global g, U.S. activity, China activity), domestic block (d1, d2).
TW_F = np.array([[0.5, 0.0, 0.0], [0.1, 0.6, 0.0], [0.1, 0.1, 0.6]])
TW_BF = np.array([[1.0, 0.0, 0.0], [0.2, 1.0, 0.0], [0.1, 0.3, 1.0]])
TW_C = np.array([[0.5, 0.1], [0.0, 0.4]])
TW_GLOBAL = np.array([0.3, 0.1])  # impact loading of d on g
TW_B = np.array([[0.2, 0.1], [0.0, 0.0]])  # partner level loadings, rows us, cn
TW_G = np.array([[0.8, 0.2], [2.0, 0.5]])  # partner slopes on the weight, rows us, cn
TW_BE = 0.5 * np.array([[1.0, 0.0], [0.3, 1.0]])


def tw_weights(n: int) -> Array:
    """U.S. weight falls from 0.25 to 0.12, China's rises from 0.05 to 0.30 (Brazil's shape)."""
    s = np.linspace(-6, 6, n)
    cn = 0.05 + 0.25 / (1 + np.exp(-s))
    us = np.linspace(0.25, 0.12, n)
    return np.column_stack([us, cn])


def _tw_impact(w: Array, slopes: Array) -> Array:
    """Domestic impact loadings on (g, us, cn) at weights ``w``: nd x nf."""
    d0 = np.zeros((2, 3))
    d0[:, 0] = TW_GLOBAL
    for j in range(2):
        d0[:, 1 + j] = TW_B[j] + slopes[j] * w[j]
    return d0


def tw_true_irf(w: Array, horizon: int, slopes: Array = TW_G) -> Array:
    """Recursive IRFs (foreign first) of the M1 DGP with weights frozen at ``w``."""
    d0 = _tw_impact(w, slopes)
    a0inv = np.eye(5)
    a0inv[3:, :3] = d0
    b = np.zeros((5, 5))
    b[:3, :3] = TW_F
    b[3:, 3:] = TW_C
    a1 = a0inv @ b
    sig = np.zeros((5, 5))
    sig[:3, :3] = TW_BF @ TW_BF.T
    sig[3:, 3:] = TW_BE @ TW_BE.T
    sigma = a0inv @ sig @ a0inv.T
    out: Array = np.einsum(
        "hik,kj->hij", ma_coefficients(a1[None], horizon), np.linalg.cholesky(sigma)
    )
    return out


def tw_dgp(n: int, seed: int, slopes: Array = TW_G) -> tuple[Array, Array]:
    """Simulate the M1 DGP; returns ``(y, w)`` with ``y`` columns g, us, cn, d1, d2."""
    rng = np.random.default_rng(seed)
    burn = 100
    w = tw_weights(n)
    w_full = np.vstack([np.repeat(w[:1], burn, axis=0), w])
    y = np.zeros((n + burn, 5))
    for t in range(1, n + burn):
        f = TW_F @ y[t - 1, :3] + TW_BF @ rng.standard_normal(3)
        d = TW_C @ y[t - 1, 3:] + _tw_impact(w_full[t], slopes) @ f + TW_BE @ rng.standard_normal(2)
        y[t, :3], y[t, 3:] = f, d
    return y[burn:], w


@dataclass(frozen=True)
class KernelDgp:
    y: Array
    beta: Array  # true impact loading of d on f, per period


def kernel_dgp(n: int, seed: int) -> KernelDgp:
    """Two variables, ``d_t = 0.4 d_{t-1} + beta_t f_t + e_t`` with
    ``beta_t = 0.5 + 0.4 sin(2 pi t / n)`` (smooth deterministic drift, as in GKY 2014)."""
    rng = np.random.default_rng(seed)
    beta = 0.5 + 0.4 * np.sin(2 * np.pi * np.arange(n) / n)
    y = np.zeros((n, 2))
    for t in range(1, n):
        f = 0.5 * y[t - 1, 0] + rng.standard_normal()
        y[t] = (f, 0.4 * y[t - 1, 1] + beta[t] * f + 0.5 * rng.standard_normal())
    return KernelDgp(y, beta)


@dataclass(frozen=True)
class TvpDgp:
    y: Array
    beta: Array  # (T, m) stacked coefficients in the m3 layout
    log_var: Array  # (T, k) log structural variances
    a: Array  # (T,) the one free contemporaneous coefficient


def tvp_dgp(n: int, seed: int, beta_sd: float = 0.01, lv_sd: float = 0.1) -> TvpDgp:
    """Two-variable TVP-VAR(1) with stochastic volatility and block exogeneity.

    Foreign ``f_t = c_f + a_f f_{t-1} + u_f``; domestic ``d_t = c_d + b1 f_{t-1} + b2 d_{t-1}
    + u_d``. Coefficients follow random walks with standard deviation 0.01; log variances
    follow random walks with standard deviation 0.1 (``beta_sd`` and ``lv_sd`` override);
    ``u_d = a_t u_f + e_d``.
    Layout of ``beta``: ``[c_f, a_f, c_d, b1, b2]``.
    """
    rng = np.random.default_rng(seed)
    beta = np.zeros((n, 5))
    beta[0] = [0.0, 0.5, 0.0, 0.3, 0.5]
    lv = np.zeros((n, 2))
    lv[0] = [0.0, np.log(0.25)]
    a = np.zeros(n)
    a[0] = 0.5
    for t in range(1, n):
        beta[t] = beta[t - 1] + beta_sd * rng.standard_normal(5)
        lv[t] = lv[t - 1] + lv_sd * rng.standard_normal(2)
        a[t] = a[t - 1] + beta_sd * rng.standard_normal()
    y = np.zeros((n, 2))
    for t in range(1, n):
        e = np.exp(lv[t] / 2) * rng.standard_normal(2)
        uf, ud = e[0], a[t] * e[0] + e[1]
        b = beta[t]
        y[t, 0] = b[0] + b[1] * y[t - 1, 0] + uf
        y[t, 1] = b[2] + b[3] * y[t - 1, 0] + b[4] * y[t - 1, 1] + ud
    return TvpDgp(y, beta, lv, a)
