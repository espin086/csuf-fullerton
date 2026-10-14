"""One block-exogenous SVAR run: estimate, test the restriction, IRFs with bands, FEVD."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from csuf_fullerton.core.svar.bootstrap import Bands, bootstrap_irf
from csuf_fullerton.core.svar.data import Array, Dataset, deterministic
from csuf_fullerton.core.svar.estimate import VarFit, fit_block_var, max_root
from csuf_fullerton.core.svar.irf import fevd, historical_decomposition
from csuf_fullerton.core.svar.tests import (
    Criteria,
    TestStat,
    criteria,
    lag_augmented_wald,
    lr_block_exogeneity,
    portmanteau,
    select_lags,
)


@dataclass(frozen=True)
class SvarSettings:
    foreign: tuple[str, ...]
    domestic: tuple[str, ...]
    lags: int | None = None
    max_lags: int = 6
    trend: bool = True
    seasonal: bool = False
    horizon: int = 24
    draws: int = 500
    level: float = 0.68
    band_method: str = "percentile"
    dmax: int = 1
    seed: int = 20261014


@dataclass(frozen=True)
class SvarResult:
    settings: SvarSettings
    names: tuple[str, ...]
    sample: tuple[str, str]
    fit: VarFit
    lag_choice: dict[str, int]
    lr: TestStat
    wald: TestStat
    crit: Criteria
    resid_check: TestStat
    root: float
    bands: Bands
    fevd: Array
    hd: Array

    @property
    def restriction_rejected(self) -> bool:
        return self.lr.pvalue < 0.05 or self.wald.pvalue < 0.05


def estimate_svar(data: Dataset, settings: SvarSettings) -> SvarResult:
    names: Sequence[str] = settings.foreign + settings.domestic
    if set(settings.foreign) & set(settings.domestic):
        raise ValueError("a variable cannot be in both blocks")
    missing = [n for n in names if n not in data.names]
    if missing:
        raise ValueError(f"columns not in data: {', '.join(missing)}")
    ds = data.select(names)
    season = ds.season if settings.seasonal else None
    det_all = deterministic(ds.nobs, settings.trend, season, ds.period)
    lag_choice = select_lags(ds.values, settings.max_lags, det_all)
    p = settings.lags or lag_choice["bic"]
    dm = settings.dmax
    y, det = ds.values[dm:], det_all[dm:]
    nf = len(settings.foreign)
    fit = fit_block_var(y, p, det, nf)
    k = len(names)
    wald = lag_augmented_wald(ds.values, p, dm, det_all, range(nf, k), range(nf))
    rng = np.random.default_rng(settings.seed)
    bands = bootstrap_irf(
        fit, y, det, settings.horizon, settings.draws, rng, settings.level, settings.band_method
    )
    return SvarResult(
        settings=settings,
        names=tuple(names),
        sample=(ds.dates[dm + p], ds.dates[-1]),
        fit=fit,
        lag_choice=lag_choice,
        lr=lr_block_exogeneity(y, p, det, nf),
        wald=wald,
        crit=criteria(fit),
        resid_check=portmanteau(fit),
        root=max_root(fit),
        bands=bands,
        fevd=fevd(bands.point),
        hd=historical_decomposition(fit),
    )
