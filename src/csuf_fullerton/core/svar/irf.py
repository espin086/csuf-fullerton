"""Recursive identification, impulse responses, FEVD and historical decomposition.

Recursive identification takes ``P = chol(Sigma_u)`` in the given column order (Lütkepohl
2005, 2.3.2). For a block-exogenous fit the foreign block is ordered first, so ``P`` and every
MA coefficient are block lower triangular and foreign responses to domestic shocks are zero.
"""

from __future__ import annotations

import numpy as np

from csuf_fullerton.core.svar.data import Array
from csuf_fullerton.core.svar.estimate import VarFit


def impact_matrix(sigma: Array) -> Array:
    """Lower-triangular ``P`` with ``P P' = Sigma``."""
    return np.linalg.cholesky(sigma)


def ma_coefficients(a: Array, horizon: int) -> Array:
    """``Phi_0 = I``, ``Phi_h = sum_{j=1}^{min(h,p)} Phi_{h-j} A_j``. Shape (H+1, k, k)."""
    p, k, _ = a.shape
    phi = np.zeros((horizon + 1, k, k))
    phi[0] = np.eye(k)
    for h in range(1, horizon + 1):
        for j in range(1, min(h, p) + 1):
            phi[h] += phi[h - j] @ a[j - 1]
    return phi


def irf(fit: VarFit, horizon: int, impact: Array | None = None) -> Array:
    """Structural responses ``Theta_h = Phi_h P``; element [h, i, j] is variable i to shock j."""
    pm = impact_matrix(fit.sigma) if impact is None else impact
    out: Array = np.einsum("hik,kj->hij", ma_coefficients(fit.A, horizon), pm)
    return out


def fevd(theta: Array) -> Array:
    """Share of the h-step forecast error variance of i due to shock j; rows sum to one."""
    cum = np.cumsum(theta**2, axis=0)
    return cum / cum.sum(axis=2, keepdims=True)


def historical_decomposition(fit: VarFit, impact: Array | None = None) -> Array:
    """Contribution of each structural shock to each variable over the sample, (T, k, k).

    ``y_t - baseline_t = sum_{s=0}^{t} Theta_s eps_{t-s}`` with ``eps = P^{-1} u``.
    """
    pm = impact_matrix(fit.sigma) if impact is None else impact
    eps = np.linalg.solve(pm, fit.resid.T).T
    n, k = eps.shape
    theta = np.einsum("hik,kj->hij", ma_coefficients(fit.A, n - 1), pm)
    out = np.zeros((n, k, k))
    for t in range(n):
        out[t] = np.einsum("sij,sj->ij", theta[: t + 1], eps[t::-1])
    return out
