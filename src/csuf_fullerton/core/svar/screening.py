"""Exogeneity screening: stages 1 to 6 of design.md (change 0004).

The screen grades every candidate block split on theory and on statistics separately, ranks
them, and reports the robustness of headline impulse responses. It never feeds a selected
split into estimation; the researcher does that.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from csuf_fullerton.core.svar.data import Array, Dataset, deterministic
from csuf_fullerton.core.svar.direction import (
    CausalOrder,
    Direction,
    direct_lingam,
    direction,
    order_agreement,
)
from csuf_fullerton.core.svar.estimate import fit_block_var, fit_var, max_root
from csuf_fullerton.core.svar.forecast import ClarkWest, clark_west
from csuf_fullerton.core.svar.irf import irf
from csuf_fullerton.core.svar.tests import (
    Criteria,
    TestStat,
    bootstrap_block_wald,
    criteria,
    holm,
    instantaneous_block,
    instantaneous_pair,
    lag_regressor_index,
    lr_block_exogeneity,
    portmanteau,
    select_lags,
    wald_zero,
)
from csuf_fullerton.core.svar.theory import Headline, Spec, Theory, enumerate_specs, theory_grade
from csuf_fullerton.core.svar.unitroot import (
    JohansenResult,
    OrderResult,
    WeakExogeneity,
    integration_order,
    johansen_rank,
    weak_exogeneity,
)

VERDICT_ORDER = {"supported": 0, "mixed": 1, "rejected": 2}
GRADE_ORDER = {"A": 0, "B": 1, "X": 2}


@dataclass(frozen=True)
class ScreenConfig:
    alpha: float = 0.05
    max_lags: int = 6
    lags: int | None = None
    lag_criterion: str = "bic"
    horizon: int = 24
    oos_fraction: float = 0.25
    portmanteau_h: int = 12
    dmax: int | None = None
    lingam_draws: int = 100
    wald_draws: int = 199
    seed: int = 20261014


@dataclass
class CandidateResult:
    spec: Spec
    grade: str
    grade_reason: str
    lr: TestStat
    wald: TestStat
    wald_p_adj: float = 1.0
    wald_p_asym: float = 1.0
    inst: TestStat | None = None
    weak: list[WeakExogeneity] = field(default_factory=list)
    weak_rejected: list[str] = field(default_factory=list)
    crit: Criteria | None = None
    clark_west: list[ClarkWest] = field(default_factory=list)
    cw_p_adj_min: float = 1.0
    resid_check: TestStat | None = None
    root: float = 0.0
    verdict: str = ""
    verdict_reason: str = ""
    lingam_agreement: float = 0.0
    lingam_agreement_lo: float = 0.0
    rank: int | None = None
    headline_irf: dict[tuple[str, str], Array] = field(default_factory=dict)


@dataclass(frozen=True)
class RobustnessRow:
    headline: Headline
    recommended_peak: float
    recommended_peak_h: int
    same_sign: int
    total: int
    specs: tuple[str, ...]


@dataclass
class ScreenResult:
    theory: Theory
    config: ScreenConfig
    nobs: int
    sample: tuple[str, str]
    orders: list[OrderResult]
    dmax: int
    johansen: JohansenResult
    lag_choice: dict[str, int]
    p: int
    granger_p: Array
    granger_p_adj: Array
    inst_p: Array
    directions: list[Direction]
    causal_order: CausalOrder
    lingam_orders: list[tuple[str, ...]]
    candidates: list[CandidateResult]
    robustness: list[RobustnessRow]
    ordering_irfs: dict[str, dict[tuple[str, str], Array]]

    @property
    def ranked(self) -> list[CandidateResult]:
        return sorted((c for c in self.candidates if c.rank), key=lambda c: c.rank or 0)

    @property
    def recommended(self) -> CandidateResult | None:
        r = self.ranked
        return r[0] if r else None


def _headline_irf(
    names: tuple[str, ...], theta: Array, heads: tuple[Headline, ...]
) -> dict[tuple[str, str], Array]:
    return {
        (h.response, h.shock): theta[:, names.index(h.response), names.index(h.shock)]
        for h in heads
    }


def _peak(x: Array) -> tuple[float, int]:
    h = int(np.argmax(np.abs(x)))
    return float(x[h]), h


def screen(data: Dataset, theory: Theory, config: ScreenConfig | None = None) -> ScreenResult:
    cfg = config or ScreenConfig()
    ds = data.select(theory.names)
    names = ds.names
    k = len(names)
    y_all = ds.values
    season = ds.season if theory.seasonal else None
    det_all = deterministic(ds.nobs, theory.trend, season, ds.period)

    # Stage 1: integration order and cointegration rank
    orders = [
        integration_order(n, y_all[:, i], theory.trend, cfg.alpha) for i, n in enumerate(names)
    ]
    dmax = cfg.dmax if cfg.dmax is not None else min(max(o.order for o in orders), 2)

    # Stage 2: lag order on the levels VAR
    lag_choice = select_lags(y_all, cfg.max_lags, det_all)
    p = cfg.lags or lag_choice[cfg.lag_criterion]
    # Johansen has no seasonal-dummy option: partial the centred dummies out first
    y_j = y_all
    if season is not None:
        sd = det_all[:, 2 if theory.trend else 1 :]
        y_j = y_all - sd @ np.linalg.lstsq(sd, y_all, rcond=None)[0]
    johansen = johansen_rank(y_j, max(p - 1, 1), theory.trend)

    # common sample: hold back dmax rows so p-lag and (p + dmax)-lag fits share the sample
    y = y_all[dmax:]
    det = det_all[dmax:]
    n_eff = y.shape[0] - p

    # Stage 3: pairwise evidence on the whole system
    la_fit = fit_var(y_all, p + dmax, det_all)
    m = det_all.shape[1]
    gp = np.full((k, k), np.nan)
    for i in range(k):
        for j in range(k):
            if i != j:
                idx = lag_regressor_index(k, m, [j], range(1, p + 1))
                gp[i, j] = wald_zero(la_fit, [i], idx).pvalue
    mask = ~np.eye(k, dtype=bool)
    gadj = np.full((k, k), np.nan)
    gadj[mask] = holm(gp[mask].tolist())
    ufit = fit_var(y, p, det)
    ip = np.full((k, k), np.nan)
    dirs = []
    eligible = {v.name for v in theory.variables if v.prior != "endogenous"}
    for i in range(k):
        for j in range(k):
            if i != j:
                ip[i, j] = instantaneous_pair(ufit.resid, i, j).pvalue
            if i < j and (names[i] in eligible) != (names[j] in eligible):
                a, b = (i, j) if names[i] in eligible else (j, i)
                dirs.append(
                    direction(names[a], ufit.resid[:, a], names[b], ufit.resid[:, b], cfg.alpha)
                )

    causal = direct_lingam(names, ufit.resid, cfg.alpha)
    rng = np.random.default_rng(cfg.seed)
    nres = ufit.resid.shape[0]
    boot_orders = [
        direct_lingam(names, ufit.resid[rng.integers(0, nres, nres)], cfg.alpha).order
        for _ in range(cfg.lingam_draws)
    ]

    # Stage 4: per-candidate battery
    weak_applies = 0 < johansen.rank < k and dmax > 0
    oos_start = round(y.shape[0] * (1 - cfg.oos_fraction))
    specs = enumerate_specs(theory)
    family_size = sum(theory_grade(theory, s)[0] != "X" for s in specs)
    # the smallest bootstrap p is 1 / (B + 1); Holm needs it well below alpha / m
    draws = (
        max(cfg.wald_draws, int(np.ceil(4 * family_size / cfg.alpha)) - 1) if cfg.wald_draws else 0
    )
    results: list[CandidateResult] = []
    for spec in specs:
        order = list(spec.foreign) + list(spec.domestic)
        idx = [names.index(n) for n in order]
        yo = y[:, idx]
        nf = len(spec.foreign)
        grade, reason = theory_grade(theory, spec)
        lr = lr_block_exogeneity(yo, p, det, nf)
        fidx = [names.index(n) for n in spec.foreign]
        didx = [names.index(n) for n in spec.domestic]
        widx = lag_regressor_index(k, m, didx, range(1, p + 1))
        asym = wald_zero(la_fit, fidx, widx)
        if draws:
            wald = bootstrap_block_wald(y_all, p, dmax, det_all, fidx, draws, rng)
        else:
            wald = TestStat(
                f"lag-augmented Wald (p={p}, d_max={dmax})", asym.stat, asym.df, asym.pvalue
            )
        rfit = fit_block_var(yo, p, det, nf)
        weak: list[WeakExogeneity] = []
        if weak_applies:
            beta_f = np.zeros((k, 0))
            if nf >= 2:
                jf = johansen_rank(y_j[:, fidx], max(p - 1, 1), theory.trend)
                beta_f = np.zeros((k, jf.rank))
                beta_f[fidx] = jf.beta
            weak = weak_exogeneity(names, y_all, det_all, johansen.beta, beta_f, p, fidx)
        weak_adj = holm([w.pvalue for w in weak]) if weak else []
        cw = clark_west(tuple(order), yo, det, p, nf, oos_start)
        theta = irf(rfit, cfg.horizon)
        agree_boot = [order_agreement(o, spec.foreign) for o in boot_orders] or [0.0]
        results.append(
            CandidateResult(
                spec=spec,
                grade=grade,
                grade_reason=reason,
                lr=lr,
                wald=wald,
                wald_p_asym=asym.pvalue,
                inst=instantaneous_block(rfit.resid, nf),
                weak=weak,
                weak_rejected=[
                    w.name for w, pa in zip(weak, weak_adj, strict=True) if pa < cfg.alpha
                ],
                crit=criteria(rfit),
                clark_west=cw,
                cw_p_adj_min=min(holm([c.pvalue for c in cw])),
                resid_check=portmanteau(rfit, cfg.portmanteau_h),
                root=max_root(rfit),
                lingam_agreement=order_agreement(causal.order, spec.foreign),
                lingam_agreement_lo=float(np.quantile(agree_boot, 0.05)),
                headline_irf=_headline_irf(tuple(order), theta, theory.headlines),
            )
        )

    # Stage 5: Holm across the admissible family, verdicts, ranking
    family = [c for c in results if c.grade != "X"]
    for c, pa in zip(family, holm([c.wald.pvalue for c in family]), strict=True):
        c.wald_p_adj = pa
    for c in results:
        if c.wald_p_adj < cfg.alpha:
            c.verdict, c.verdict_reason = (
                "rejected",
                (f"domestic lags Granger-cause the foreign block (Holm p = {c.wald_p_adj:.3g})"),
            )
        elif c.weak_rejected:
            c.verdict, c.verdict_reason = (
                "mixed",
                ("lag restriction holds but not weakly exogenous: " + ", ".join(c.weak_rejected)),
            )
        elif c.wald.pvalue < cfg.alpha:
            c.verdict, c.verdict_reason = (
                "mixed",
                (f"survives the Holm family but the unadjusted Wald p = {c.wald.pvalue:.3g}"),
            )
        elif dmax == 0 and c.cw_p_adj_min < cfg.alpha:
            # Clark-West asymptotics assume stationary data; with unit roots it is a flag only
            c.verdict, c.verdict_reason = (
                "mixed",
                (
                    "in-sample restriction holds but domestic lags improve foreign "
                    f"forecasts out of sample (Clark-West Holm p = {c.cw_p_adj_min:.3g})"
                ),
            )
        else:
            c.verdict, c.verdict_reason = "supported", "lag restriction not rejected"
    ranked = sorted(
        family,
        key=lambda c: (
            GRADE_ORDER[c.grade],
            VERDICT_ORDER[c.verdict],
            c.crit.bic if c.crit else 0.0,
            -c.wald.pvalue,
        ),
    )
    for r, c in enumerate(ranked, start=1):
        c.rank = r

    # Stage 6: robustness of headline responses
    rec = ranked[0] if ranked else None
    survivors = [c for c in ranked if c.verdict != "rejected"]
    ordering_irfs: dict[str, dict[tuple[str, str], Array]] = {}
    if rec is not None:
        for dom in theory.orderings:
            if sorted(dom) != sorted(rec.spec.domestic) or tuple(dom) == rec.spec.domestic:
                continue
            order = list(rec.spec.foreign) + list(dom)
            yo = y[:, [names.index(n) for n in order]]
            theta = irf(fit_block_var(yo, p, det, len(rec.spec.foreign)), cfg.horizon)
            ordering_irfs[" > ".join(dom)] = _headline_irf(tuple(order), theta, theory.headlines)
    robustness = []
    if rec is not None:
        for h in theory.headlines:
            key = (h.response, h.shock)
            peak, ph = _peak(rec.headline_irf[key])
            series = [(c.spec.name, c.headline_irf[key]) for c in survivors]
            series += [(f"ordering {o}", v[key]) for o, v in ordering_irfs.items()]
            same = sum(1 for _, s in series if np.sign(s[ph]) == np.sign(peak) and peak != 0)
            robustness.append(
                RobustnessRow(h, peak, ph, same, len(series), tuple(s for s, _ in series))
            )

    return ScreenResult(
        theory=theory,
        config=cfg,
        nobs=n_eff,
        sample=(ds.dates[dmax + p], ds.dates[-1]),
        orders=orders,
        dmax=dmax,
        johansen=johansen,
        lag_choice=lag_choice,
        p=p,
        granger_p=gp,
        granger_p_adj=gadj,
        inst_p=ip,
        directions=dirs,
        causal_order=causal,
        lingam_orders=boot_orders,
        candidates=results,
        robustness=robustness,
        ordering_irfs=ordering_irfs,
    )
