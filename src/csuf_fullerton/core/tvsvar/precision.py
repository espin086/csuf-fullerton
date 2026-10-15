"""Precision-based simulation smoother for random-walk states (Chan and Jeliazkov 2009).

Model: ``obs_t`` contributes precision ``G_t`` and linear term ``g_t`` for state ``s_t``;
states follow ``s_t = s_{t-1} + v_t``, ``v_t ~ N(0, Q)``, with prior ``s_1 ~ N(s0, P1^-1)``.
The joint posterior precision of ``(s_1, ..., s_n)`` is block tridiagonal, stored in
LAPACK upper banded form and factorised with ``scipy.linalg.cholesky_banded``.
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import cho_solve_banded, cholesky_banded, solve_banded

from csuf_fullerton.core.svar.data import Array


def banded_precision(obs_prec: Array, state_prec: Array, prior_prec: Array) -> Array:
    """Upper banded storage (bandwidth ``2d - 1``) of the posterior precision."""
    n, d, _ = obs_prec.shape
    u = 2 * d - 1
    big = n * d
    ab = np.zeros((u + 1, big))
    diag = obs_prec.copy()
    diag[:-1] += state_prec
    diag[1:] += state_prec
    diag[0] += prior_prec
    t = np.arange(n)
    for a in range(d):
        for b in range(a, d):
            ab[u + a - b, t * d + b] = diag[:, a, b]
    off = -state_prec
    t1 = np.arange(n - 1)
    for a in range(d):
        for b in range(d):
            ab[u + a - (d + b), (t1 + 1) * d + b] = off[a, b]
    return ab


def draw_states(
    obs_prec: Array,
    obs_lin: Array,
    state_prec: Array,
    prior_mean: Array,
    prior_prec: Array,
    rng: np.random.Generator | None,
) -> tuple[Array, Array]:
    """Posterior mean and one draw (or the mean twice when ``rng`` is None), both (n, d)."""
    n, d = obs_lin.shape
    ab = banded_precision(obs_prec, state_prec, prior_prec)
    chol = cholesky_banded(ab, lower=False)
    rhs = obs_lin.copy()
    rhs[0] += prior_prec @ prior_mean
    mean = cho_solve_banded((chol, False), rhs.reshape(-1))
    if rng is None:
        return mean.reshape(n, d), mean.reshape(n, d)
    z = rng.standard_normal(n * d)
    draw = mean + solve_banded((0, 2 * d - 1), chol, z)
    return mean.reshape(n, d), draw.reshape(n, d)
