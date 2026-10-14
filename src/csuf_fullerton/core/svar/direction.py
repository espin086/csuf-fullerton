"""Pairwise contemporaneous direction from non-Gaussianity (Hyvärinen and Smith 2013).

For standardized residuals ``x`` and ``y`` with correlation ``rho``, the tanh approximation
to the pairwise likelihood ratio is ``R = rho * E[x tanh(y) - tanh(x) y]``; ``R > 0`` points
to ``x -> y``. The tanh form assumes super-Gaussian (heavy-tailed) disturbances; for
sub-Gaussian pairs the sign is flipped, following the paper's sign-of-kurtosis adjustment.
Without non-Gaussianity the direction is not identified, so the measure is gated on a
Jarque-Bera rejection for both series and is advisory only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from csuf_fullerton.core.svar.data import Array


@dataclass(frozen=True)
class Direction:
    cause: str
    effect: str
    r: float
    jb_p_cause: float
    jb_p_effect: float
    identified: bool  # both residuals non-Gaussian at alpha

    @property
    def verdict(self) -> str:
        if not self.identified:
            return "not identified (Gaussian residuals)"
        return f"{self.cause} -> {self.effect}" if self.r > 0 else f"{self.effect} -> {self.cause}"


def pairwise_r(x: Array, y: Array) -> float:
    x = (x - x.mean()) / x.std()
    y = (y - y.mean()) / y.std()
    rho = float(np.mean(x * y))
    r = rho * float(np.mean(x * np.tanh(y) - np.tanh(x) * y))
    if stats.kurtosis(x) + stats.kurtosis(y) < 0:
        r = -r
    return r


def direction(name_x: str, x: Array, name_y: str, y: Array, alpha: float = 0.05) -> Direction:
    jx = float(stats.jarque_bera(x).pvalue)
    jy = float(stats.jarque_bera(y).pvalue)
    return Direction(name_x, name_y, pairwise_r(x, y), jx, jy, jx < alpha and jy < alpha)


@dataclass(frozen=True)
class CausalOrder:
    order: tuple[str, ...]
    nongaussian_share: float  # share of residual series rejecting Jarque-Bera at alpha


def direct_lingam(names: tuple[str, ...], resid: Array, alpha: float = 0.05) -> CausalOrder:
    """DirectLiNGAM ordering of contemporaneous residuals (Shimizu et al. 2011) with the
    Hyvärinen-Smith pairwise measure. At each step the variable whose pairwise measures most
    consistently point away from it (``score_i = -sum_j min(0, R_ij)^2``) is taken as the most
    exogenous, then regressed out of the remaining residuals."""
    r = resid - resid.mean(axis=0)
    remaining = list(range(len(names)))
    order: list[int] = []
    while len(remaining) > 1:
        best, best_score = remaining[0], -np.inf
        for i in remaining:
            score = -sum(min(0.0, pairwise_r(r[:, i], r[:, j])) ** 2 for j in remaining if j != i)
            if score > best_score:
                best, best_score = i, score
        order.append(best)
        remaining.remove(best)
        xi = r[:, best]
        for j in remaining:
            r[:, j] = r[:, j] - (xi @ r[:, j]) / (xi @ xi) * xi
    order += remaining
    jb = [float(stats.jarque_bera(resid[:, i]).pvalue) < alpha for i in range(len(names))]
    return CausalOrder(tuple(names[i] for i in order), float(np.mean(jb)))


def order_agreement(order: tuple[str, ...], foreign: tuple[str, ...]) -> float:
    """Share of (foreign, domestic) pairs that the causal order puts foreign first."""
    pos = {n: i for i, n in enumerate(order)}
    dom = [n for n in order if n not in foreign]
    pairs = [(f, d) for f in foreign for d in dom]
    return float(np.mean([pos[f] < pos[d] for f, d in pairs])) if pairs else 1.0
