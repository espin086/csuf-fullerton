"""M3: Bayesian TVP-VAR with stochastic volatility and block exogeneity (Primiceri 2005).

``y_t = Z_t beta_t + u_t``, ``A_t u_t = e_t``, ``e_t ~ N(0, diag(exp(g_t)))``, with random
walks for ``beta_t``, the free elements of the unit lower-triangular ``A_t`` (row by row),
and the log variances ``g_t``.

Block exogeneity: foreign equations (the first ``nf``) contain only a constant and foreign
lags, so ``beta_t`` has no element for a domestic lag in a foreign equation; and with the
foreign block ordered first, ``A_t`` lower triangular puts no current domestic variable in a
foreign equation. Both hold at every date and in every draw.

Gibbs order follows the Del Negro and Primiceri (2015) corrigendum: ``beta``, ``A``, the
hyperparameters ``(Q, S, W)``, then the mixture indicators ``s``, then the volatilities. The
mixture is the seven-component approximation of Kim, Shephard and Chib (1998). Priors are
Primiceri's, centred on OLS estimates from a training sample (``training > 0``) or, when the
sample is too short for one, from the full sample (reported as a weakness).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats

from csuf_fullerton.core.svar.data import Array, lag_matrix
from csuf_fullerton.core.svar.irf import ma_coefficients
from csuf_fullerton.core.tvsvar.precision import draw_states

KSC_Q = np.array([0.00730, 0.10556, 0.00002, 0.04395, 0.34001, 0.24566, 0.25750])
KSC_M = np.array([-10.12999, -3.97281, -8.56686, 2.77786, 0.61942, 1.79518, -1.08819]) - 1.2704
KSC_V2 = np.array([5.79596, 2.61369, 5.17950, 0.16735, 0.64009, 0.34023, 1.26261])
OFFSET = 0.001  # Primiceri's constant inside log(e^2 + c)


@dataclass(frozen=True)
class TvpSettings:
    p: int = 2
    draws: int = 5000
    burn: int = 2000
    thin: int = 5
    training: int = 0
    k_q: float = 0.01
    k_s: float = 0.1
    k_w: float = 0.01
    tau: int = 40  # prior degrees of freedom for Q (Primiceri's training-sample size)
    seed: int = 20261014


@dataclass(frozen=True)
class Layout:
    """Regressor layout: equation ``i`` uses lag columns ``cols[i]`` of ``lag_matrix(y, p)``."""

    k: int
    nf: int
    p: int
    cols: tuple[tuple[int, ...], ...]

    @property
    def sizes(self) -> tuple[int, ...]:
        return tuple(1 + len(c) for c in self.cols)

    @property
    def m(self) -> int:
        return sum(self.sizes)


def layout(k: int, nf: int, p: int) -> Layout:
    fcols = tuple(lag * k + j for lag in range(p) for j in range(nf))
    allc = tuple(range(k * p))
    return Layout(k, nf, p, tuple(fcols if i < nf else allc for i in range(k)))


def design(lay: Layout, y: Array) -> Array:
    """``Z`` with shape (n, k, m) for rows ``t = p..T-1``."""
    lags = lag_matrix(y, lay.p)
    n = lags.shape[0]
    z = np.zeros((n, lay.k, lay.m))
    pos = 0
    for i, cols in enumerate(lay.cols):
        z[:, i, pos] = 1.0
        z[:, i, pos + 1 : pos + 1 + len(cols)] = lags[:, list(cols)]
        pos += 1 + len(cols)
    return z


@dataclass(frozen=True)
class Prior:
    beta0: Array
    v_beta: Array
    a0: tuple[Array, ...]  # per row i >= 1, length i
    v_a: tuple[Array, ...]
    g0: Array
    ols_resid: Array


def ols_prior(lay: Layout, y: Array) -> Prior:
    """Equation-by-equation OLS: coefficients, their covariances, residual-based A and logs."""
    z = design(lay, y)
    yy = y[lay.p :]
    n = len(yy)
    betas, vs, resid = [], [], np.zeros_like(yy)
    pos = 0
    for i, size in enumerate(lay.sizes):
        x = z[:, i, pos : pos + size]
        b, *_ = np.linalg.lstsq(x, yy[:, i], rcond=None)
        e = yy[:, i] - x @ b
        s2 = e @ e / max(n - size, 1)
        betas.append(b)
        vs.append(s2 * np.linalg.inv(x.T @ x))
        resid[:, i] = e
        pos += size
    m = lay.m
    v_beta = np.zeros((m, m))
    pos = 0
    for v in vs:
        v_beta[pos : pos + len(v), pos : pos + len(v)] = v
        pos += len(v)
    a0, v_a, ehat = [], [], resid[:, :1].copy()
    g0 = [np.log(resid[:, 0] @ resid[:, 0] / n)]
    for i in range(1, lay.k):
        x = -resid[:, :i]
        b, *_ = np.linalg.lstsq(x, resid[:, i], rcond=None)
        e = resid[:, i] - x @ b
        s2 = e @ e / max(n - i, 1)
        a0.append(b)
        v_a.append(s2 * np.linalg.inv(x.T @ x))
        g0.append(np.log(e @ e / n))
        ehat = np.hstack([ehat, e[:, None]])
    return Prior(np.concatenate(betas), v_beta, tuple(a0), tuple(v_a), np.array(g0), resid)


def a_matrix(a_rows: Sequence[Array], k: int) -> Array:
    """Unit lower-triangular ``A`` from per-row free elements (row ``i`` has ``i`` entries)."""
    a = np.eye(k)
    for i in range(1, k):
        a[i, :i] = a_rows[i - 1]
    return a


@dataclass(frozen=True)
class TvpResult:
    layout: Layout
    settings: TvpSettings
    beta: Array  # (draws, n, m)
    a: Array  # (draws, n, k(k-1)/2)
    g: Array  # (draws, n, k) log structural variances
    q_diag: Array  # (draws, m)
    accepted_draws: int
    prior_from_training: bool

    def a_rows(self, d: int, t: int) -> list[Array]:
        out, pos = [], 0
        for i in range(1, self.layout.k):
            out.append(self.a[d, t, pos : pos + i])
            pos += i
        return out


def _iw(scale: Array, df: float, rng: np.random.Generator) -> Array:
    out = stats.invwishart(df=df, scale=scale).rvs(random_state=rng)
    return np.atleast_2d(np.asarray(out, dtype=float))


def gibbs(y: Array, nf: int, settings: TvpSettings) -> TvpResult:
    s = settings
    k = y.shape[1]
    lay = layout(k, nf, s.p)
    rng = np.random.default_rng(s.seed)
    if s.training:
        if s.training <= max(lay.sizes) + s.p + 5:
            raise ValueError("training sample too short for the OLS prior")
        prior = ols_prior(lay, y[: s.training])
        y = y[s.training - s.p :]
    else:
        prior = ols_prior(lay, y)
    z = design(lay, y)
    yy = y[s.p :]
    n, m = len(yy), lay.m
    # Primiceri priors
    p1_beta = np.linalg.inv(4.0 * prior.v_beta)
    q_scale = s.k_q**2 * s.tau * prior.v_beta
    q = s.k_q**2 * prior.v_beta
    s_scale = [s.k_s**2 * (i + 1) * prior.v_a[i - 1] for i in range(1, k)]
    s_cur = [s.k_s**2 * prior.v_a[i - 1] for i in range(1, k)]
    w_scale = s.k_w**2 * (1 + k) * np.eye(k)
    w = s.k_w**2 * np.eye(k)
    a_rows = [np.repeat(prior.a0[i - 1][None], n, axis=0) for i in range(1, k)]
    g = np.repeat(prior.g0[None], n, axis=0)
    beta = np.repeat(prior.beta0[None], n, axis=0)
    keep = (s.draws - s.burn) // s.thin
    if keep < 1:
        raise ValueError("draws must exceed burn-in by at least one thinning interval")
    out_b = np.empty((keep, n, m))
    out_a = np.empty((keep, n, k * (k - 1) // 2))
    out_g = np.empty((keep, n, k))
    out_q = np.empty((keep, m))
    kept = 0
    for it in range(s.draws):
        # 1. beta | A, g, Q
        amat = np.array([a_matrix([r[t] for r in a_rows], k) for t in range(n)])
        oinv = np.einsum("tji,tj,tjk->tik", amat, np.exp(-g), amat)
        obs_prec = np.einsum("tim,tij,tjn->tmn", z, oinv, z)
        obs_lin = np.einsum("tim,tij,tj->tm", z, oinv, yy)
        _, beta = draw_states(obs_prec, obs_lin, np.linalg.inv(q), prior.beta0, p1_beta, rng)
        u = yy - np.einsum("tim,tm->ti", z, beta)
        # 2. A rows | beta, g, S
        for i in range(1, k):
            r = -u[:, :i]
            prec_e = np.exp(-g[:, i])
            op = np.einsum("ti,tj,t->tij", r, r, prec_e)
            ol = r * (u[:, i] * prec_e)[:, None]
            p1 = np.linalg.inv(4.0 * prior.v_a[i - 1])
            _, a_rows[i - 1] = draw_states(
                op, ol, np.linalg.inv(s_cur[i - 1]), prior.a0[i - 1], p1, rng
            )
        # 3. hyperparameters
        db = np.diff(beta, axis=0)
        q = _iw(q_scale + db.T @ db, s.tau + n - 1, rng)
        for i in range(1, k):
            da = np.diff(a_rows[i - 1], axis=0)
            s_cur[i - 1] = _iw(s_scale[i - 1] + da.T @ da, (i + 1) + n - 1, rng)
        dg = np.diff(g, axis=0)
        w = _iw(w_scale + dg.T @ dg, (1 + k) + n - 1, rng)
        # 4. mixture indicators | beta, A, g   (Del Negro and Primiceri 2015 order)
        amat = np.array([a_matrix([r[t] for r in a_rows], k) for t in range(n)])
        e = np.einsum("tij,tj->ti", amat, u)
        estar = np.log(e**2 + OFFSET)
        dens = (
            np.log(KSC_Q)
            - 0.5 * np.log(KSC_V2)
            - 0.5 * (estar[..., None] - g[..., None] - KSC_M) ** 2 / KSC_V2
        )
        dens = np.exp(dens - dens.max(axis=-1, keepdims=True))
        cdf = np.cumsum(dens / dens.sum(axis=-1, keepdims=True), axis=-1)
        sidx = (rng.random((n, k, 1)) > cdf).sum(axis=-1)
        sidx = np.minimum(sidx, len(KSC_Q) - 1)
        # 5. log variances | s, beta, A, W
        v2 = KSC_V2[sidx]
        op = np.zeros((n, k, k))
        op[:, np.arange(k), np.arange(k)] = 1.0 / v2
        ol = (estar - KSC_M[sidx]) / v2
        _, g = draw_states(op, ol, np.linalg.inv(w), prior.g0, np.eye(k) / 4.0, rng)
        if it >= s.burn and (it - s.burn) % s.thin == 0 and kept < keep:
            out_b[kept] = beta
            out_a[kept] = np.hstack(a_rows)
            out_g[kept] = g
            out_q[kept] = np.diag(q)
            kept += 1
    return TvpResult(lay, s, out_b, out_a, out_g, out_q, kept, s.training > 0)


def coefficient_matrices(lay: Layout, beta_t: Array) -> tuple[Array, Array]:
    """Constant vector and lag matrices (p, k, k) from one date's ``beta``."""
    k, p = lay.k, lay.p
    c = np.zeros(k)
    a = np.zeros((p, k, k))
    pos = 0
    for i, cols in enumerate(lay.cols):
        c[i] = beta_t[pos]
        for j, col in enumerate(cols):
            lag, var = divmod(col, k)
            a[lag, i, var] = beta_t[pos + 1 + j]
        pos += 1 + len(cols)
    return c, a


def irf_at(res: TvpResult, t: int, horizon: int) -> Array:
    """Posterior draws of structural IRFs at row ``t`` of the estimation sample, (D, H+1, k, k)."""
    lay = res.layout
    out = np.empty((res.accepted_draws, horizon + 1, lay.k, lay.k))
    for d in range(res.accepted_draws):
        _, a = coefficient_matrices(lay, res.beta[d, t])
        impact = np.linalg.solve(
            a_matrix(res.a_rows(d, t), lay.k), np.diag(np.exp(res.g[d, t] / 2))
        )
        out[d] = np.einsum("hik,kj->hij", ma_coefficients(a, horizon), impact)
    return out


def inefficiency(x: Array, max_lag: int = 50) -> float:
    """``1 + 2 sum rho_j`` with Bartlett weights (Primiceri 2005, appendix)."""
    x = x - x.mean()
    v = x @ x
    if v == 0:
        return 1.0
    n = len(x)
    lags = min(max_lag, n - 1)
    rho = np.array([x[: n - j] @ x[j:] / v for j in range(1, lags + 1)])
    wts = 1 - np.arange(1, lags + 1) / (lags + 1)
    return float(1 + 2 * np.sum(wts * rho))


def geweke_z(x: Array) -> float:
    """Geweke (1992) z: first 10% against last 50%, variances scaled by inefficiency."""
    n = len(x)
    a, b = x[: n // 10], x[n // 2 :]
    va = a.var() * inefficiency(a) / max(len(a), 1)
    vb = b.var() * inefficiency(b) / max(len(b), 1)
    if va + vb == 0:
        return 0.0
    return float((a.mean() - b.mean()) / np.sqrt(va + vb))


def diagnostics(res: TvpResult) -> dict[str, dict[str, float]]:
    """Median and max inefficiency factor and max |Geweke z| per parameter block, computed on
    the time-averaged states (one series per element) to keep it cheap."""
    blocks = {
        "beta": res.beta.mean(axis=1),
        "a": res.a.mean(axis=1),
        "log_var": res.g.mean(axis=1),
        "q_diag": res.q_diag,
    }
    out: dict[str, dict[str, float]] = {}
    for name, arr in blocks.items():
        ifs = [inefficiency(arr[:, j]) for j in range(arr.shape[1])]
        zs = [abs(geweke_z(arr[:, j])) for j in range(arr.shape[1])]
        out[name] = {
            "median_inefficiency": float(np.median(ifs)) if ifs else 0.0,
            "max_inefficiency": float(np.max(ifs)) if ifs else 0.0,
            "max_abs_geweke_z": float(np.max(zs)) if zs else 0.0,
        }
    return out
