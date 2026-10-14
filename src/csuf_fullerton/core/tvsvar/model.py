"""One time-varying SVAR run per model rung (M0 to M3), from a Dataset and trade weights."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace

import numpy as np

from csuf_fullerton.core.svar.data import Array, Dataset, deterministic
from csuf_fullerton.core.svar.model import SvarResult, SvarSettings, estimate_svar
from csuf_fullerton.core.svar.tests import TestStat, select_lags
from csuf_fullerton.core.tvsvar import m0, m1, m2, m3
from csuf_fullerton.core.tvsvar.weights import TradeWeights, monthly

MODELS = ("m0", "m1", "m2", "m3")


@dataclass(frozen=True)
class TvSettings:
    foreign: tuple[str, ...]
    domestic: tuple[str, ...]
    partners: tuple[tuple[str, tuple[str, ...]], ...] = ()  # (partner, its foreign columns)
    lags: int | None = None
    max_lags: int = 6
    trend: bool = True
    seasonal: bool = False
    horizon: int = 24
    draws: int = 500
    level: float = 0.68
    frozen_years: tuple[int, ...] = ()
    variant: str = "interacted"
    band_method: str = "hall"
    lr_draws: int = 199
    break_date: str | None = None
    break_draws: int = 199
    bandwidth_exp: float = 0.5
    kernel_step: int = 1
    headlines: tuple[tuple[str, str], ...] = ()  # (response, shock)
    m3_vars: tuple[str, ...] = ()
    m3_foreign: int = 0
    m3_diff12: tuple[str, ...] = ()  # M3 columns replaced by 12-month differences (y/y growth)
    tvp: m3.TvpSettings = field(default_factory=m3.TvpSettings)
    seed: int = 20261014

    @property
    def names(self) -> tuple[str, ...]:
        return self.foreign + self.domestic


def _prepare(ds: Dataset, s: TvSettings) -> tuple[Dataset, Array, int]:
    if set(s.foreign) & set(s.domestic):
        raise ValueError("a variable cannot be in both blocks")
    missing = [n for n in s.names if n not in ds.names]
    if missing:
        raise ValueError(f"columns not in data: {', '.join(missing)}")
    sub = ds.select(s.names)
    det = deterministic(sub.nobs, s.trend, sub.season if s.seasonal else None, sub.period)
    p = s.lags or select_lags(sub.values, s.max_lags, det)["bic"]
    return sub, det, p


def _spec(s: TvSettings, p: int, variant: str) -> m1.TwSpec:
    names = s.names
    cols = tuple(tuple(names.index(c) for c in pc) for _, pc in s.partners)
    return m1.TwSpec(len(s.foreign), len(names), tuple(n for n, _ in s.partners), cols, p, variant)


def _frozen(tw: TradeWeights, years: Sequence[int]) -> list[tuple[int, Array]]:
    return [(y, tw.at(y)) for y in years]


@dataclass(frozen=True)
class M0Result:
    svar: SvarResult
    stability: list[m0.BreakTest]
    break_date: str | None
    sup_date: str


def run_m0(ds: Dataset, s: TvSettings) -> M0Result:
    sub, det, p = _prepare(ds, s)
    svar = estimate_svar(
        sub,
        SvarSettings(
            s.foreign,
            s.domestic,
            p,
            s.max_lags,
            s.trend,
            s.seasonal,
            s.horizon,
            s.draws,
            s.level,
            "percentile",
            0,
            s.seed,
        ),
    )
    brk = None
    if s.break_date:
        if s.break_date not in sub.dates:
            raise ValueError(f"break date {s.break_date} is not in the sample")
        brk = sub.dates.index(s.break_date) - p
    rng = np.random.default_rng(s.seed)
    tests = m0.stability_tests(sub.values, p, det, len(s.foreign), brk, rng, s.break_draws)
    sup_row = tests[-1].break_index + p
    return M0Result(svar, tests, s.break_date, sub.dates[sup_row])


@dataclass(frozen=True)
class M1Result:
    names: tuple[str, ...]
    sample: tuple[str, str]
    p: int
    variant: str
    fits: dict[str, m1.TwFit]
    tests: list[TestStat]
    bootstrap_p: dict[str, float]  # test name -> bootstrap p-value
    bands: m1.FrozenBands
    weights: Array  # T_eff x J path used in estimation
    weight_dates: tuple[str, ...]
    partners: tuple[str, ...]
    loading: dict[str, Array]  # "response|shock" -> impact loading path
    frozen_weights: dict[int, list[float]]
    weight_window: int
    weight_lag: int


def run_m1(ds: Dataset, tw: TradeWeights, s: TvSettings) -> M1Result:
    if not s.partners:
        raise ValueError("M1 needs --partners")
    if len(s.frozen_years) < 2:
        raise ValueError("M1 needs at least two --frozen-years")
    sub, det, p = _prepare(ds, s)
    w = monthly(tw, sub.dates)
    y = sub.values
    fits = {v: m1.fit_tw(_spec(s, p, v), y, det, w) for v in m1.VARIANTS}
    center = fits["constant"].center
    fits = {v: m1.fit_tw(_spec(s, p, v), y, det, w, center) for v in m1.VARIANTS}
    tests = [
        m1.lr_nested(fits["levels"], fits["interacted"], "LR: weights do not change transmission"),
        m1.lr_nested(fits["star"], fits["interacted"], "LR: GVAR star loading is enough"),
        m1.lr_nested(fits["constant"], fits["levels"], "LR: weight levels do not enter"),
    ]
    if len(s.partners) > 1:
        tests.append(m1.wald_equal_slopes(fits["interacted"]))
    fit = fits[s.variant]
    rng = np.random.default_rng(s.seed)
    boot_p = {}
    if s.lr_draws:
        boot_p[tests[0].name] = m1.bootstrap_lr(
            fits["levels"], "interacted", y, det, w, s.lr_draws, rng
        )
        boot_p[tests[1].name] = m1.bootstrap_lr(
            fits["star"], "interacted", y, det, w, s.lr_draws, rng
        )
    bands = m1.bootstrap_frozen(
        fit,
        y,
        det,
        w,
        _frozen(tw, s.frozen_years),
        s.horizon,
        s.draws,
        rng,
        s.level,
        s.band_method,
    )
    names = s.names
    loading = {}
    for resp, shock in s.headlines:
        if resp in s.domestic and shock in s.foreign:
            loading[f"{resp}|{shock}"] = m1.loading_path(
                fit, w[p:], s.domestic.index(resp), s.foreign.index(shock)
            )
    return M1Result(
        names,
        (sub.dates[p], sub.dates[-1]),
        p,
        s.variant,
        fits,
        tests,
        boot_p,
        bands,
        w[p:],
        sub.dates[p:],
        tuple(n for n, _ in s.partners),
        loading,
        {yr: tw.at(yr).tolist() for yr in s.frozen_years},
        tw.window,
        tw.lag,
    )


@dataclass(frozen=True)
class M2Result:
    names: tuple[str, ...]
    p: int
    bandwidth: float
    dates: tuple[str, ...]
    path: m2.KernelPath
    weight_corr: dict[str, float]  # "response|shock" -> corr(loading path, partner weight)


def run_m2(ds: Dataset, s: TvSettings, tw: TradeWeights | None = None) -> M2Result:
    sub, det, p = _prepare(ds, s)
    kp = m2.kernel_svar(
        sub.values, p, det, len(s.foreign), s.horizon, s.bandwidth_exp, s.kernel_step
    )
    dates = tuple(sub.dates[t] for t in kp.taus)
    corr: dict[str, float] = {}
    if tw is not None and s.partners:
        w = monthly(tw, dates)
        for resp, shock in s.headlines:
            for j, (_, cols) in enumerate(s.partners):
                if shock in cols and resp in s.domestic:
                    path = kp.impact[:, s.domestic.index(resp), s.foreign.index(shock)]
                    corr[f"{resp}|{shock}"] = float(np.corrcoef(path, w[:, j])[0, 1])
    return M2Result(s.names, p, kp.bandwidth, dates, kp, corr)


@dataclass(frozen=True)
class M3Result:
    names: tuple[str, ...]
    dates: tuple[str, ...]
    result: m3.TvpResult
    irf_dates: tuple[str, ...]
    irfs: Array  # (n_dates, D, H+1, k, k)
    diagnostics: dict[str, dict[str, float]]
    diff12: tuple[str, ...] = ()


def run_m3(ds: Dataset, s: TvSettings, irf_dates: Sequence[str]) -> M3Result:
    names = s.m3_vars or s.names
    sub = ds.select(names)
    values, sdates = sub.values, sub.dates
    if s.m3_diff12:
        bad = [n for n in s.m3_diff12 if n not in names]
        if bad:
            raise ValueError(f"--m3-yoy columns not in --m3-vars: {', '.join(bad)}")
        values = values.copy()
        for n in s.m3_diff12:
            i = names.index(n)
            values[12:, i] = values[12:, i] - values[:-12, i]
        values, sdates = values[12:], sdates[12:]
    nf = s.m3_foreign or sum(1 for n in names if n in s.foreign)
    tvp = replace(s.tvp, seed=s.seed)
    # Centre each series: near-constant levels (cycle indices around 100) make the intercept
    # almost collinear with the lags and the OLS prior precision near singular. Responses and
    # volatilities do not depend on the means; the time-varying intercepts absorb them.
    res = m3.gibbs(values - values.mean(axis=0), nf, tvp)
    start = (tvp.training - tvp.p if tvp.training else 0) + tvp.p
    dates = sdates[start:]
    rows = []
    for d in irf_dates:
        if d not in dates:
            raise ValueError(f"IRF date {d} is outside the M3 estimation sample")
        rows.append(m3.irf_at(res, dates.index(d), s.horizon))
    return M3Result(
        tuple(names), dates, res, tuple(irf_dates), np.array(rows), m3.diagnostics(res), s.m3_diff12
    )
