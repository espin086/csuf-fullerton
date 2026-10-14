"""Reduced-form VAR estimation: unrestricted OLS and the two-block restricted system.

The block-exogenous system follows Zha (1999): with a block-recursive A0 the likelihood
factors into one piece per block, so each block is estimated by OLS on its own.

* Foreign block: ``x_t`` on deterministic terms and ``p`` lags of ``x`` only.
* Domestic block: ``z_t`` on deterministic terms, current ``x_t`` and ``p`` lags of all
  variables. Mapping back to the reduced form gives ``z`` coefficients
  ``C + D0 B_x`` and residuals ``e_z + D0 u_x``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from csuf_fullerton.core.svar.data import Array, lag_matrix


@dataclass(frozen=True)
class VarFit:
    """Reduced form ``y_t = Phi d_t + A_1 y_{t-1} + ... + A_p y_{t-p} + u_t``.

    ``A`` has shape (p, k, k); ``Phi`` has shape (k, m). ``sigma`` is the ML covariance
    ``U'U / T``; ``nparams`` counts free coefficients in the whole system.
    """

    p: int
    nf: int  # size of the foreign block, 0 for an unrestricted VAR
    A: Array
    Phi: Array
    resid: Array
    sigma: Array
    nparams: int
    nobs: int
    X: Array  # regressor matrix of the unrestricted form [d_t, lags]
    Y: Array  # left-hand side rows t = p..T-1

    @property
    def k(self) -> int:
        return int(self.A.shape[1])

    @property
    def coef(self) -> Array:
        """Stacked coefficients (m + k p) x k in the column order of ``X``."""
        lags = np.vstack([self.A[i].T for i in range(self.p)]) if self.p else np.empty((0, self.k))
        return np.vstack([self.Phi.T, lags])


def _ols(y: Array, x: Array) -> tuple[Array, Array]:
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    return beta, y - x @ beta


def _split(beta: Array, m: int, k: int, p: int) -> tuple[Array, Array]:
    phi = beta[:m].T
    a = (
        np.stack([beta[m + i * k : m + (i + 1) * k].T for i in range(p)])
        if p
        else np.empty((0, k, k))
    )
    return phi, a


def fit_var(y: Array, p: int, det: Array) -> VarFit:
    """Unrestricted VAR(p) by equation-by-equation OLS. ``det`` has one row per row of ``y``."""
    t, k = y.shape
    if t - p <= det.shape[1] + k * p:
        raise ValueError("not enough observations for the number of parameters")
    x = np.hstack([det[p:], lag_matrix(y, p)])
    yy = y[p:]
    beta, u = _ols(yy, x)
    m = det.shape[1]
    phi, a = _split(beta, m, k, p)
    n = yy.shape[0]
    return VarFit(p, 0, a, phi, u, u.T @ u / n, beta.size, n, x, yy)


def fit_block_var(y: Array, p: int, det: Array, nf: int) -> VarFit:
    """Block-exogenous VAR(p): first ``nf`` columns of ``y`` form the foreign block."""
    t, k = y.shape
    if not 0 < nf < k:
        raise ValueError("foreign block must hold between 1 and k-1 variables")
    m = det.shape[1]
    lags = lag_matrix(y, p)
    yy = y[p:]
    d = det[p:]
    n = yy.shape[0]
    # foreign lag columns inside the lag-major lag matrix
    fcols = [lag * k + j for lag in range(p) for j in range(nf)]
    xf = np.hstack([d, lags[:, fcols]])
    bf, uf = _ols(yy[:, :nf], xf)
    xd = np.hstack([d, yy[:, :nf], lags])
    bd, ed = _ols(yy[:, nf:], xd)
    d0 = bd[m : m + nf].T  # nd x nf impact of current x on z
    # reduced form of the foreign block in the full regressor layout
    bf_full = np.zeros((m + k * p, nf))
    bf_full[:m] = bf[:m]
    for i, col in enumerate(fcols):
        bf_full[m + col] = bf[m + i]
    cz = np.vstack([bd[:m], bd[m + nf :]])  # coefficients on [d, lags]
    bz_full = cz + bf_full @ d0.T
    beta = np.hstack([bf_full, bz_full])
    u = np.hstack([uf, ed + uf @ d0.T])
    phi, a = _split(beta, m, k, p)
    nparams = bf.size + bd.size
    x = np.hstack([d, lags])
    if t - p <= xd.shape[1]:
        raise ValueError("not enough observations for the number of parameters")
    return VarFit(p, nf, a, phi, u, u.T @ u / n, nparams, n, x, yy)


def companion(a: Array) -> Array:
    p, k, _ = a.shape
    top = np.hstack(list(a))
    if p == 1:
        return top
    bottom = np.hstack([np.eye(k * (p - 1)), np.zeros((k * (p - 1), k))])
    return np.vstack([top, bottom])


def max_root(fit: VarFit) -> float:
    """Largest modulus of the companion matrix eigenvalues (< 1 means stable)."""
    return float(np.max(np.abs(np.linalg.eigvals(companion(fit.A)))))
