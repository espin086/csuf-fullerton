"""M2: kernel time-varying block-exogenous SVAR (Giraitis, Kapetanios and Yates 2014).

At each date ``tau`` both blocks are estimated by weighted least squares with Gaussian kernel
weights ``K((t - tau) / H)``, ``H = n ** h``. Each block keeps its own regressors, so the
foreign block never sees domestic variables at any date. The local covariance is the
kernel-weighted residual covariance. Impulse responses at ``tau`` use the local coefficients
("frozen at tau"). Pointwise standard errors of the local impact loadings use the
heteroskedasticity-robust sandwich ``(X'KX)^-1 X'K^2 diag(u^2) X (X'KX)^-1``.

The local fit needs enough data: the Kish effective sample at the sample ends must be at
least twice the regressors per domestic equation, or the run stops. GKY's ``h = 0.5`` suits
small systems; an eight-variable monthly system needs a wider window.

A flat kernel (``h = inf``) gives every row weight one, so every date reproduces the
constant 0002 estimate. That is the parity check in the replication suite.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from csuf_fullerton.core.svar.data import Array
from csuf_fullerton.core.tvsvar.m1 import TwSpec, deterministic_width, fit_tw, frozen_irf


@dataclass(frozen=True)
class KernelPath:
    bandwidth: float
    taus: tuple[int, ...]  # rows of y at which local estimates are reported
    impact: Array  # (n_tau, nd, nf) local impact loadings D_0
    impact_se: Array  # same shape, sandwich standard errors
    irf: Array  # (n_tau, H+1, k, k)


def kernel_weights(n: int, tau: int, bandwidth: float) -> Array:
    if np.isinf(bandwidth):
        return np.ones(n)
    t = np.arange(n)
    out: Array = np.exp(-0.5 * ((t - tau) / bandwidth) ** 2)
    return out


def bandwidth_for(n: int, exponent: float) -> float:
    return float("inf") if np.isinf(exponent) else float(n**exponent)


def effective_nobs(weights: Array) -> float:
    """Kish effective sample size ``(sum k)^2 / sum k^2`` of a set of kernel weights."""
    return float(weights.sum() ** 2 / (weights**2).sum())


def kernel_svar(
    y: Array,
    p: int,
    det: Array,
    nf: int,
    horizon: int,
    exponent: float = 0.5,
    step: int = 1,
) -> KernelPath:
    """Local estimates at every ``step``-th row from ``p`` to the end of ``y``."""
    t, k = y.shape
    spec = TwSpec(nf, k, (), (), p, "constant")
    w = np.zeros((t, 0))
    h = bandwidth_for(t, exponent)
    taus = tuple(range(p, t, step))
    impacts, ses, irfs = [], [], []
    m = det.shape[1]
    q = m + nf + k * p  # regressors in a domestic equation
    edge = effective_nobs(kernel_weights(t, p, h)[p:])
    if edge < 2 * q:
        raise ValueError(
            f"bandwidth {h:.1f} leaves {edge:.0f} effective observations at the sample ends for "
            f"{q} regressors per equation; raise --bandwidth-exp or cut lags or dummies"
        )
    for tau in taus:
        rw = kernel_weights(t, tau, h)
        fit = fit_tw(spec, y, det, w, row_weights=rw)
        assert deterministic_width(fit) == m  # noqa: S101
        kk = rw[p:]
        x = fit.x_d
        xkx_inv = np.linalg.inv(x.T @ (x * kk[:, None]))
        cols = slice(m, m + nf)
        imp = fit.coef_d[cols].T  # nd x nf
        se = np.zeros_like(imp)
        for e in range(k - nf):
            meat = x.T @ (x * (kk**2 * fit.resid_d[:, e] ** 2)[:, None])
            v = xkx_inv @ meat @ xkx_inv
            se[e] = np.sqrt(np.diag(v)[cols])
        impacts.append(imp)
        ses.append(se)
        irfs.append(frozen_irf(fit, np.zeros(0), horizon))
    return KernelPath(h, taus, np.array(impacts), np.array(ses), np.array(irfs))
