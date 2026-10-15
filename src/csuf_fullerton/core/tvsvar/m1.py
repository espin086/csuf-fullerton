"""M1: trade-weighted block-exogenous SVAR (design.md, "M1").

The foreign block is the 0002 foreign block: OLS of each foreign variable on deterministic
terms and ``p`` lags of the foreign variables only. The domestic block regresses ``z_t`` on
deterministic terms, current and lagged foreign variables (``l = 0..p``), ``p`` own lags and,
for the weighted variants, the partner weights themselves. Partner variables enter by variant:

* ``constant``: raw partner variables; identical to the 0002 estimator.
* ``levels``: ``constant`` plus the weights as regressors (the null model of the LR test).
* ``star``: GVAR loading, ``sum_j w_jt (x_{j,v,t-l} - mean)`` for each variable type ``v``.
* ``interacted``: raw partner variables and ``w_jt (x_{j,t-l} - mean)`` (Towbin and Weber 2013).

Partner variables are centred at their sample mean inside the products so the product does
not pick up ``mean * w_jt`` as a disguised trend. Impulse responses are computed with the
weights frozen at a chosen year (Cesa-Bianchi et al. 2012); the centring only moves the
constant, so it does not change them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats

from csuf_fullerton.core.svar.data import Array, lag_matrix
from csuf_fullerton.core.svar.estimate import VarFit
from csuf_fullerton.core.svar.irf import irf
from csuf_fullerton.core.svar.tests import TestStat

VARIANTS = ("constant", "levels", "star", "interacted")


@dataclass(frozen=True)
class TwSpec:
    """Column layout of ``y``: foreign columns first (``nf``), then domestic.

    ``partner_cols[j][v]`` is the column of variable type ``v`` for partner ``j``; every
    partner has the same number of variable types. Columns not listed are global variables.
    """

    nf: int
    k: int
    partners: tuple[str, ...]
    partner_cols: tuple[tuple[int, ...], ...]
    p: int
    variant: str = "interacted"

    def __post_init__(self) -> None:
        if self.variant not in VARIANTS:
            raise ValueError(f"variant must be one of {VARIANTS}")
        if not 0 < self.nf < self.k:
            raise ValueError("foreign block must hold between 1 and k-1 variables")
        if self.p < 1:
            raise ValueError("lag order must be at least 1")
        if len(self.partners) != len(self.partner_cols):
            raise ValueError("one column tuple per partner")
        sizes = {len(c) for c in self.partner_cols}
        if len(sizes) > 1:
            raise ValueError("every partner needs the same variable types")
        flat = [c for cols in self.partner_cols for c in cols]
        if len(set(flat)) != len(flat) or any(not 0 <= c < self.nf for c in flat):
            raise ValueError("partner columns must be distinct foreign columns")

    @property
    def nd(self) -> int:
        return self.k - self.nf

    @property
    def nv(self) -> int:
        return len(self.partner_cols[0]) if self.partner_cols else 0

    @property
    def global_cols(self) -> tuple[int, ...]:
        flat = {c for cols in self.partner_cols for c in cols}
        return tuple(c for c in range(self.nf) if c not in flat)

    def with_variant(self, variant: str) -> TwSpec:
        return TwSpec(self.nf, self.k, self.partners, self.partner_cols, self.p, variant)


@dataclass(frozen=True)
class TwFit:
    spec: TwSpec
    phi_f: Array  # nf x m deterministic coefficients of the foreign block
    f_lags: Array  # (p, nf, nf)
    coef_d: Array  # q x nd domestic coefficients in design column order
    resid_f: Array
    resid_d: Array
    sigma_f: Array
    sigma_d: Array
    x_d: Array
    center: Array  # mean of each foreign column (only partner columns are used)
    nobs: int

    @property
    def q(self) -> int:
        return int(self.coef_d.shape[0])


def _row(spec: TwSpec, y: Array, t: int, det_t: Array, w_t: Array, center: Array) -> Array:
    """Domestic regressors at time ``t`` (needs rows ``t - p .. t`` of ``y``)."""
    parts: list[Array] = [det_t]
    v = spec.variant
    for lag in range(spec.p + 1):
        f = y[t - lag, : spec.nf]
        parts.append(f[list(spec.global_cols)])
        if v in ("constant", "levels", "interacted"):
            parts.append(np.array([f[c] for cols in spec.partner_cols for c in cols]))
        if v == "star":
            parts.append(
                np.array(
                    [
                        sum(
                            w_t[j] * (f[cols[i]] - center[cols[i]])
                            for j, cols in enumerate(spec.partner_cols)
                        )
                        for i in range(spec.nv)
                    ]
                )
            )
        if v == "interacted":
            parts.append(
                np.array(
                    [
                        w_t[j] * (f[c] - center[c])
                        for j, cols in enumerate(spec.partner_cols)
                        for c in cols
                    ]
                )
            )
    if v != "constant":
        parts.append(w_t)
    for lag in range(1, spec.p + 1):
        parts.append(y[t - lag, spec.nf :])
    return np.concatenate(parts)


def domestic_design(spec: TwSpec, y: Array, det: Array, w: Array, center: Array) -> Array:
    return np.vstack([_row(spec, y, t, det[t], w[t], center) for t in range(spec.p, len(y))])


def _ols(yy: Array, x: Array, rw: Array | None = None) -> tuple[Array, Array]:
    if rw is None:
        beta, *_ = np.linalg.lstsq(x, yy, rcond=None)
    else:
        s = np.sqrt(rw)[:, None]
        beta, *_ = np.linalg.lstsq(x * s, yy * s, rcond=None)
    return beta, yy - x @ beta


def _cov(u: Array, rw: Array | None) -> Array:
    if rw is None:
        out: Array = u.T @ u / len(u)
        return out
    wu: Array = (u * rw[:, None]).T @ u / rw.sum()
    return wu


def fit_tw(
    spec: TwSpec,
    y: Array,
    det: Array,
    w: Array,
    center: Array | None = None,
    row_weights: Array | None = None,
) -> TwFit:
    """Estimate both blocks by OLS (weighted least squares when ``row_weights``, one weight
    per row of ``y``, is given). ``w`` is T x J (one column per partner), aligned with ``y``."""
    t, k = y.shape
    if k != spec.k or det.shape[0] != t or w.shape != (t, len(spec.partners)):
        raise ValueError("y, det and w must share rows; y needs spec.k columns")
    ctr = y[:, : spec.nf].mean(axis=0) if center is None else center
    p, nf = spec.p, spec.nf
    m = det.shape[1]
    rw = None if row_weights is None else row_weights[p:]
    xf = np.hstack([det[p:], lag_matrix(y[:, :nf], p)])
    bf, uf = _ols(y[p:, :nf], xf, rw)
    f_lags = np.stack([bf[m + i * nf : m + (i + 1) * nf].T for i in range(p)])
    xd = domestic_design(spec, y, det, w, ctr)
    if xd.shape[0] <= xd.shape[1]:
        raise ValueError("not enough observations for the number of parameters")
    bd, ud = _ols(y[p:, nf:], xd, rw)
    n = xd.shape[0]
    return TwFit(spec, bf[:m].T, f_lags, bd, uf, ud, _cov(uf, rw), _cov(ud, rw), xd, ctr, n)


def _blocks(fit: TwFit, w: Array) -> tuple[Array, Array]:
    """``D`` (p+1, nd, nf) foreign loadings at frozen weights ``w`` and ``C`` (p, nd, nd)."""
    s = fit.spec
    m = deterministic_width(fit)
    b = fit.coef_d
    d = np.zeros((s.p + 1, s.nd, s.nf))
    pos = m
    for lag in range(s.p + 1):
        for c in s.global_cols:
            d[lag, :, c] = b[pos]
            pos += 1
        if s.variant in ("constant", "levels", "interacted"):
            for cols in s.partner_cols:
                for c in cols:
                    d[lag, :, c] += b[pos]
                    pos += 1
        if s.variant == "star":
            for i in range(s.nv):
                for j, cols in enumerate(s.partner_cols):
                    d[lag, :, cols[i]] += w[j] * b[pos]
                pos += 1
        if s.variant == "interacted":
            for j, cols in enumerate(s.partner_cols):
                for c in cols:
                    d[lag, :, c] += w[j] * b[pos]
                    pos += 1
    if s.variant != "constant":
        pos += len(s.partners)
    c_mat = np.zeros((s.p, s.nd, s.nd))
    for lag in range(s.p):
        c_mat[lag] = b[pos : pos + s.nd].T
        pos += s.nd
    return d, c_mat


def _width(s: TwSpec) -> int:
    """Foreign regressors per lag in the domestic design."""
    g = len(s.global_cols)
    raw = s.nv * len(s.partners)
    return {
        "constant": g + raw,
        "levels": g + raw,
        "star": g + s.nv,
        "interacted": g + 2 * raw,
    }[s.variant]


def deterministic_width(fit: TwFit) -> int:
    s = fit.spec
    mains = 0 if s.variant == "constant" else len(s.partners)
    return fit.q - _width(s) * (s.p + 1) - mains - s.nd * s.p


def frozen_system(fit: TwFit, w: Array) -> VarFit:
    """Reduced form of the system with weights held at ``w``, as a ``VarFit`` for 0002's IRFs."""
    s = fit.spec
    d, c_mat = _blocks(fit, w)
    k, nf = s.k, s.nf
    a0inv = np.eye(k)
    a0inv[nf:, :nf] = d[0]
    a = np.zeros((s.p, k, k))
    for lag in range(s.p):
        b = np.zeros((k, k))
        b[:nf, :nf] = fit.f_lags[lag]
        b[nf:, :nf] = d[lag + 1]
        b[nf:, nf:] = c_mat[lag]
        a[lag] = a0inv @ b
    sig = np.zeros((k, k))
    sig[:nf, :nf] = fit.sigma_f
    sig[nf:, nf:] = fit.sigma_d
    sigma = a0inv @ sig @ a0inv.T
    empty = np.zeros((0, k))
    return VarFit(s.p, nf, a, np.zeros((k, 1)), empty, sigma, fit.q * s.nd, fit.nobs, empty, empty)


def frozen_irf(fit: TwFit, w: Array, horizon: int) -> Array:
    return irf(frozen_system(fit, w), horizon)


def loading_path(fit: TwFit, w: Array, response: int, shock: int) -> Array:
    """Impact loading ``D_0`` of domestic ``response`` (0-based within the domestic block) on
    foreign column ``shock`` over the sample's weight path ``w`` (T x J)."""
    return np.array([_blocks(fit, wt)[0][0, response, shock] for wt in w])


def _logdet(m: Array) -> float:
    sign, val = np.linalg.slogdet(m)
    if sign <= 0:
        raise ValueError("covariance matrix is not positive definite")
    return float(val)


def lr_nested(restricted: TwFit, unrestricted: TwFit, name: str) -> TestStat:
    """Sims-corrected LR on the domestic block; the foreign block is common to both."""
    c = unrestricted.q
    stat = (unrestricted.nobs - c) * (_logdet(restricted.sigma_d) - _logdet(unrestricted.sigma_d))
    df = (unrestricted.q - restricted.q) * unrestricted.spec.nd
    return TestStat(name, float(stat), df, float(stats.chi2.sf(stat, df)))


def wald_equal_slopes(fit: TwFit) -> TestStat:
    """Wald test that every partner's interaction slopes equal the first partner's."""
    s = fit.spec
    if s.variant != "interacted" or len(s.partners) < 2:
        raise ValueError("needs the interacted variant with at least two partners")
    m = deterministic_width(fit)
    g, raw = len(s.global_cols), s.nv * len(s.partners)
    rows: list[tuple[int, int]] = []
    for lag in range(s.p + 1):
        base = m + lag * _width(s) + g + raw
        for j in range(1, len(s.partners)):
            for v in range(s.nv):
                rows.append((base + v, base + j * s.nv + v))
    n, q = fit.x_d.shape
    sig = fit.resid_d.T @ fit.resid_d / (n - q)
    xtx_inv = np.linalg.inv(fit.x_d.T @ fit.x_d)
    nd = s.nd
    r = np.zeros((len(rows) * nd, q * nd))
    for e in range(nd):
        for i, (a, b) in enumerate(rows):
            r[e * len(rows) + i, e * q + a] = 1.0
            r[e * len(rows) + i, e * q + b] = -1.0
    beta = fit.coef_d.T.reshape(-1)  # equation-major vec
    theta = r @ beta
    cov = r @ np.kron(sig, xtx_inv) @ r.T
    stat = float(theta @ np.linalg.solve(cov, theta))
    df = len(rows) * nd
    return TestStat("equal partner slopes Wald", stat, df, float(stats.chi2.sf(stat, df)))


def simulate_tw(fit: TwFit, y0: Array, det: Array, w: Array, u_f: Array, u_d: Array) -> Array:
    """Regenerate ``y`` from the fitted system along the observed weight path."""
    s = fit.spec
    p, nf = s.p, s.nf
    n = u_f.shape[0]
    y = np.zeros((n + p, s.k))
    y[:p] = y0
    for t in range(p, n + p):
        f = fit.phi_f @ det[t] + u_f[t - p]
        for lag in range(1, p + 1):
            f += fit.f_lags[lag - 1] @ y[t - lag, :nf]
        y[t, :nf] = f
        y[t, nf:] = _row(s, y, t, det[t], w[t], fit.center) @ fit.coef_d + u_d[t - p]
    return y


@dataclass(frozen=True)
class FrozenBands:
    years: tuple[int, ...]
    point: Array  # (Y, H+1, k, k)
    lower: Array
    upper: Array
    diff_point: Array  # (Y-1, H+1, k, k): year i minus the first year
    diff_lower: Array
    diff_upper: Array
    draws: int
    level: float


def bootstrap_frozen(
    fit: TwFit,
    y: Array,
    det: Array,
    w: Array,
    frozen: Sequence[tuple[int, Array]],
    horizon: int,
    draws: int,
    rng: np.random.Generator,
    level: float = 0.68,
    method: str = "hall",
) -> FrozenBands:
    """Residual bootstrap with the observed weight path held fixed in every draw. Differences
    between frozen years are formed draw by draw, so their bands test the change itself.
    ``hall`` intervals reflect the bootstrap quantiles around the estimate, which corrects the
    downward bias of persistent levels VARs (Kilian and Lutkepohl 2017, 12.2);
    ``percentile`` uses the raw quantiles."""
    if method not in ("hall", "percentile"):
        raise ValueError("method must be hall or percentile")
    years = tuple(yr for yr, _ in frozen)
    point = np.stack([frozen_irf(fit, wv, horizon) for _, wv in frozen])
    u = np.hstack([fit.resid_f, fit.resid_d])
    u = u - u.mean(axis=0)
    n = u.shape[0]
    nf = fit.spec.nf
    out = np.empty((draws, *point.shape))
    for b in range(draws):
        idx = rng.integers(0, n, n)
        ys = simulate_tw(fit, y[: fit.spec.p], det, w, u[idx, :nf], u[idx, nf:])
        fb = fit_tw(fit.spec, ys, det, w, fit.center)
        out[b] = np.stack([frozen_irf(fb, wv, horizon) for _, wv in frozen])
    a = (1 - level) / 2
    diffs = out[:, 1:] - out[:, :1]
    dpoint = point[1:] - point[:1]

    def band(est: Array, sample: Array) -> tuple[Array, Array]:
        lo, hi = np.quantile(sample, a, axis=0), np.quantile(sample, 1 - a, axis=0)
        return (2 * est - hi, 2 * est - lo) if method == "hall" else (lo, hi)

    lo, hi = band(point, out)
    dlo, dhi = band(dpoint, diffs)
    return FrozenBands(years, point, lo, hi, dpoint, dlo, dhi, draws, level)


def bootstrap_lr(
    restricted: TwFit,
    unrestricted_variant: str,
    y: Array,
    det: Array,
    w: Array,
    draws: int,
    rng: np.random.Generator,
) -> float:
    """Bootstrap p-value of the nested LR: data are generated from the restricted fit along the
    observed weight path, and both models are re-estimated on every draw."""
    observed = lr_nested(
        restricted,
        fit_tw(restricted.spec.with_variant(unrestricted_variant), y, det, w, restricted.center),
        "",
    ).stat
    u = np.hstack([restricted.resid_f, restricted.resid_d])
    u = u - u.mean(axis=0)
    n, nf = u.shape[0], restricted.spec.nf
    stats_ = np.empty(draws)
    for b in range(draws):
        idx = rng.integers(0, n, n)
        ys = simulate_tw(restricted, y[: restricted.spec.p], det, w, u[idx, :nf], u[idx, nf:])
        fr = fit_tw(restricted.spec, ys, det, w, restricted.center)
        fu = fit_tw(
            restricted.spec.with_variant(unrestricted_variant), ys, det, w, restricted.center
        )
        stats_[b] = lr_nested(fr, fu, "").stat
    return float((1 + np.sum(stats_ >= observed)) / (draws + 1))
