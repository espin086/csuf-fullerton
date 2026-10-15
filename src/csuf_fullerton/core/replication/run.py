"""Case functions: each takes pinned data tables and case settings and returns metric values.

Pure: tables arrive as pandas DataFrames already read and hash-checked by the CLI.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
import pandas as pd

from csuf_fullerton.core.replication.cases import Case, CaseResult, evaluate
from csuf_fullerton.core.svar.data import Array, Dataset, deterministic, make_dataset
from csuf_fullerton.core.svar.estimate import fit_block_var, fit_var
from csuf_fullerton.core.svar.irf import irf
from csuf_fullerton.core.svar.model import SvarSettings, estimate_svar
from csuf_fullerton.core.tvsvar import m0, m1, m2, m3
from csuf_fullerton.core.tvsvar.precision import draw_states
from csuf_fullerton.core.tvsvar.simulate import (
    TW_G,
    kernel_dgp,
    tvp_dgp,
    tw_dgp,
    tw_true_irf,
)
from csuf_fullerton.core.tvsvar.weights import (
    TradeWeights,
    annual_shares,
    monthly,
    required_years,
    smooth,
)

Tables = Mapping[str, pd.DataFrame]
Settings = Mapping[str, Any]
CaseFn = Callable[[Tables, Settings, int], dict[str, float]]


def dataset(df: pd.DataFrame, start: str | None = None, end: str | None = None) -> Dataset:
    d = df.copy()
    d["date"] = d["date"].astype(str)
    if start:
        d = d[d["date"] >= start]
    if end:
        d = d[d["date"] <= end]
    names = [c for c in d.columns if c != "date"]
    months = [int(x[5:7]) if len(x) >= 7 and x[4] == "-" else 1 for x in d["date"]]
    return make_dataset(names, d[names].to_numpy(float), d["date"].tolist(), months, 12)


def trade_weights(
    df: pd.DataFrame,
    partners: list[str],
    window: int,
    lag: int,
    dates: list[str] | tuple[str, ...] = (),
) -> TradeWeights:
    """Smoothed weights from a long ``year, partner, value`` table; ``dates`` (the sample) makes
    every year it needs mandatory, so a gap there raises instead of being skipped."""
    table = {(str(r.partner), int(r.year)): float(r.value) for r in df.itertuples()}
    need = required_years(dates, window, lag) if dates else ()
    return smooth(annual_shares(table, partners, require=need), partners, window, lag)


def _tw_inputs(t: Tables, s: Settings) -> tuple[Dataset, Array, m1.TwSpec, Array, TradeWeights]:
    names = list(s["foreign"]) + list(s["domestic"])
    ds = dataset(t["data"], s.get("start"), s.get("end")).select(names)
    det = deterministic(ds.nobs, s.get("trend", True), ds.season if s.get("seasonal") else None)
    parts = [(p, tuple(c)) for p, c in s["partners"]]
    tw = trade_weights(
        t["trade"], [p for p, _ in parts], s.get("window", 3), s.get("weights_lag", 1), ds.dates
    )
    cols = tuple(tuple(names.index(c) for c in pc) for _, pc in parts)
    spec = m1.TwSpec(
        len(s["foreign"]),
        len(names),
        tuple(p for p, _ in parts),
        cols,
        s["lags"],
        s.get("variant", "interacted"),
    )
    return ds, det, spec, monthly(tw, ds.dates), tw


# ---------------------------------------------------------------- M0


def m0_parity_statsmodels(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    from statsmodels.tsa.api import VAR

    ds = dataset(t["data"], s.get("start"), s.get("end"))
    p = int(s["lags"])
    ours = fit_var(ds.values, p, np.ones((ds.nobs, 1))).coef
    ref = np.asarray(VAR(ds.values).fit(p, trend="c").params)
    return {"max_abs_diff": float(np.abs(ours - ref).max())}


def m0_nicaragua_regression(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    ds = dataset(t["data"])
    st = SvarSettings(
        tuple(s["foreign"]),
        tuple(s["domestic"]),
        int(s["lags"]),
        6,
        True,
        True,
        int(s["horizon"]),
        int(s["draws"]),
        0.68,
        "hall",
        int(s["dmax"]),
        seed,
    )
    res = estimate_svar(ds, st)
    ref = t["irf"]
    names = res.names
    got = np.array(
        [
            res.bands.point[int(r.h), names.index(r.response), names.index(r.shock)]
            for r in ref.itertuples()
        ]
    )
    return {"max_abs_diff": float(np.abs(got - ref["irf"].to_numpy()).max())}


def m0_sim_break(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    """Rejection rate of the bootstrap sup-LR at 5% over ``reps`` M1-DGP samples; slopes
    ``scale * TW_G`` (0 = constant coefficients, the size case)."""
    rej = []
    for r in range(int(s["reps"])):
        y, _ = tw_dgp(int(s["n"]), seed + r, s["scale"] * TW_G)
        out = m0.stability_tests(
            y, 1, np.ones((len(y), 1)), 3, None, np.random.default_rng(seed + r), int(s["draws"])
        )
        rej.append(out[-1].bootstrap_p <= 0.05)
    return {"rejection_rate": float(np.mean(rej))}


# ---------------------------------------------------------------- M1


def m1_parity_constant(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    ds, det, spec, w, _ = _tw_inputs(t, {**s, "variant": "constant"})
    fit = m1.fit_tw(spec, ds.values, det, w)
    ref = fit_block_var(ds.values, spec.p, det, spec.nf)
    h = int(s.get("horizon", 24))
    return {"max_abs_diff": float(np.abs(m1.frozen_irf(fit, w[0], h) - irf(ref, h)).max())}


def m1_sim_coverage(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    """Coverage of the true frozen-year IRFs and of their difference (d1 to the China shock)."""
    n, reps, draws, hz = int(s["n"]), int(s["reps"]), int(s["draws"]), int(s["horizon"])
    level = float(s.get("level", 0.90))
    spec = m1.TwSpec(3, 5, ("us", "cn"), ((1,), (2,)), 1, "interacted")
    cover_a, cover_b, cover_d = [], [], []
    for r in range(reps):
        y, w = tw_dgp(n, seed + r)
        det = np.ones((n, 1))
        fit = m1.fit_tw(spec, y, det, w)
        frozen = [(0, w[0]), (1, w[-1])]
        b = m1.bootstrap_frozen(
            fit, y, det, w, frozen, hz, draws, np.random.default_rng(seed + r), level
        )
        ta, tb = tw_true_irf(w[0], hz)[:, 3, 2], tw_true_irf(w[-1], hz)[:, 3, 2]
        cover_a.append(np.mean((b.lower[0, :, 3, 2] <= ta) & (ta <= b.upper[0, :, 3, 2])))
        cover_b.append(np.mean((b.lower[1, :, 3, 2] <= tb) & (tb <= b.upper[1, :, 3, 2])))
        td = tb - ta
        cover_d.append(np.mean((b.diff_lower[0, :, 3, 2] <= td) & (td <= b.diff_upper[0, :, 3, 2])))
    return {
        "coverage_first": float(np.mean(cover_a)),
        "coverage_last": float(np.mean(cover_b)),
        "coverage_diff": float(np.mean(cover_d)),
    }


def m1_sim_lr_size(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    spec = m1.TwSpec(3, 5, ("us", "cn"), ((1,), (2,)), 1, "interacted")
    rej_null: list[bool] = []
    rej_alt: list[bool] = []
    for r in range(int(s["reps"])):
        for scale, store in ((0.0, rej_null), (1.0, rej_alt)):
            y, w = tw_dgp(int(s["n"]), seed + r, scale * TW_G)
            det = np.ones((len(y), 1))
            fi = m1.fit_tw(spec, y, det, w)
            fl = m1.fit_tw(spec.with_variant("levels"), y, det, w, fi.center)
            store.append(m1.lr_nested(fl, fi, "lr").pvalue <= 0.05)
    return {"size": float(np.mean(rej_null)), "power": float(np.mean(rej_alt))}


def m1_direction(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    """Change in the mean response over horizons ``[h0, h1]`` from year ``a`` to year ``b``
    weights, for each (response, shock) pair listed in ``pairs``."""
    ds, det, spec, w, tw = _tw_inputs(t, s)
    fit = m1.fit_tw(spec, ds.values, det, w)
    names = list(s["foreign"]) + list(s["domestic"])
    h0, h1 = int(s["h0"]), int(s["h1"])
    ia = m1.frozen_irf(fit, tw.at(int(s["year_a"])), h1)
    ib = m1.frozen_irf(fit, tw.at(int(s["year_b"])), h1)
    out = {}
    for key, (resp, shock) in s["pairs"].items():
        i, j = names.index(resp), names.index(shock)
        out[key] = float(ib[h0 : h1 + 1, i, j].mean() - ia[h0 : h1 + 1, i, j].mean())
    return out


# ---------------------------------------------------------------- M2


def m2_parity_flat(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    names = list(s["foreign"]) + list(s["domestic"])
    ds = dataset(t["data"], s.get("start"), s.get("end")).select(names)
    det = deterministic(ds.nobs, True, ds.season, 12)
    p, nf, h = int(s["lags"]), len(s["foreign"]), int(s.get("horizon", 12))
    kp = m2.kernel_svar(ds.values, p, det, nf, h, float("inf"), step=max(ds.nobs // 3, 1))
    ref = irf(fit_block_var(ds.values, p, det, nf), h)
    return {"max_abs_diff": float(max(np.abs(x - ref).max() for x in kp.irf))}


def m2_sim_sinusoid(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    def mad(n: int) -> float:
        vals = []
        for r in range(int(s["reps"])):
            d = kernel_dgp(n, seed + r)
            kp = m2.kernel_svar(d.y, 1, np.ones((n, 1)), 1, 0, float(s.get("exponent", 0.5)))
            vals.append(np.abs(kp.impact[:, 0, 0] - d.beta[1:]).mean())
        return float(np.mean(vals))

    small, large = mad(int(s["n_small"])), mad(int(s["n_large"]))
    return {"mad_small": small, "mad_large": large, "mad_ratio": large / small}


def m2_brazil_regression(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    ds, det, spec, _, tw = _tw_inputs(t, {**s, "variant": "constant"})
    kp = m2.kernel_svar(ds.values, spec.p, det, spec.nf, 0, float(s.get("exponent", 0.5)))
    names = list(s["foreign"]) + list(s["domestic"])
    resp, shock = s["pair"]
    path = kp.impact[:, names.index(resp) - spec.nf, names.index(shock)]
    dates = [ds.dates[i] for i in kp.taus]
    wj = monthly(tw, dates)[:, [p for p, _ in s["partners"]].index(s["partner"])]
    q = max(len(path) // 5, 1)
    return {
        "change_last_minus_first_fifth": float(path[-q:].mean() - path[:q].mean()),
        "corr_with_weight": float(np.corrcoef(path, wj)[0, 1]),
    }


# ---------------------------------------------------------------- M3


def m3_parity_kalman(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    """Conditional posterior mean of the coefficient states equals the Kalman smoother."""
    import statsmodels.api as sm

    rng = np.random.default_rng(seed)
    d = tvp_dgp(int(s["n"]), seed)
    lay = m3.layout(2, 1, 1)
    z = m3.design(lay, d.y)
    yy = d.y[1:]
    n, m = len(yy), lay.m
    q = np.diag(rng.uniform(1e-4, 1e-3, m))
    om = np.array([np.diag(rng.uniform(0.2, 1.0, 2)) for _ in range(n)])
    om[:, 0, 1] = om[:, 1, 0] = 0.1
    b0, p1 = rng.normal(size=m), 0.5 * np.eye(m)
    oinv = np.linalg.inv(om)
    mean, _ = draw_states(
        np.einsum("tim,tij,tjn->tmn", z, oinv, z),
        np.einsum("tim,tij,tj->tm", z, oinv, yy),
        np.linalg.inv(q),
        b0,
        p1,
        None,
    )
    mod = sm.tsa.statespace.MLEModel(yy, k_states=m)
    mod.ssm["design"] = np.transpose(z, (1, 2, 0))
    mod.ssm["obs_cov"] = np.transpose(om, (1, 2, 0))
    mod.ssm["transition"] = np.eye(m)
    mod.ssm["selection"] = np.eye(m)
    mod.ssm["state_cov"] = q
    mod.ssm.initialize_known(b0, np.linalg.inv(p1))
    ref = mod.ssm.smooth().smoothed_state.T
    return {"max_abs_diff": float(np.abs(mean - ref).max())}


def _tvp(s: Settings, seed: int) -> m3.TvpSettings:
    return m3.TvpSettings(
        p=int(s.get("p", 1)),
        draws=int(s["draws"]),
        burn=int(s["burn"]),
        thin=int(s.get("thin", 1)),
        training=int(s.get("training", 0)),
        seed=seed,
    )


def m3_sim_coverage(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    bc, gc, block = [], [], []
    for r in range(int(s["reps"])):
        d = tvp_dgp(int(s["n"]), seed + r, float(s["beta_sd"]), float(s["lv_sd"]))
        res = m3.gibbs(d.y, 1, _tvp(s, seed + r))
        lo, hi = np.quantile(res.beta, [0.05, 0.95], axis=0)
        bc.append(np.mean((lo <= d.beta[1:]) & (d.beta[1:] <= hi)))
        glo, ghi = np.quantile(res.g, [0.05, 0.95], axis=0)
        gc.append(np.mean((glo <= d.log_var[1:]) & (d.log_var[1:] <= ghi)))
        resp = m3.irf_at(res, len(d.y) // 2, 4)
        block.append(np.abs(resp[:, :, 0, 1]).max())
    return {
        "beta_coverage": float(np.mean(bc)),
        "log_var_coverage": float(np.mean(gc)),
        "max_foreign_response_to_domestic": float(np.max(block)),
    }


def _year(q: str) -> float:
    return int(q[:4]) + (int(q[-1]) - 1) / 4 if "Q" in q else int(q[:4]) + (int(q[5:7]) - 1) / 12


def m3_primiceri(t: Tables, s: Settings, seed: int) -> dict[str, float]:
    df = t["data"]
    cols = list(s["columns"])
    res = m3.gibbs(df[cols].to_numpy(float), 0, _tvp(s, seed))
    tr, p = int(s.get("training", 0)), int(s.get("p", 2))
    dates = df["date"].astype(str).tolist()[(tr - p if tr else 0) + p :]
    vol = np.median(np.exp(res.g / 2), axis=0)
    i = cols.index(s["rate"])
    peak = int(np.argmax(vol[:, i]))
    base = dates.index(s["base_date"])
    return {
        "rate_vol_peak_year": _year(dates[peak]),
        "rate_vol_peak_over_base": float(vol[peak, i] / vol[base, i]),
    }


FUNCTIONS: dict[str, CaseFn] = {
    "m0_parity_statsmodels": m0_parity_statsmodels,
    "m0_nicaragua_regression": m0_nicaragua_regression,
    "m0_sim_break": m0_sim_break,
    "m1_parity_constant": m1_parity_constant,
    "m1_sim_coverage": m1_sim_coverage,
    "m1_sim_lr_size": m1_sim_lr_size,
    "m1_direction": m1_direction,
    "m2_parity_flat": m2_parity_flat,
    "m2_sim_sinusoid": m2_sim_sinusoid,
    "m2_brazil_regression": m2_brazil_regression,
    "m3_parity_kalman": m3_parity_kalman,
    "m3_sim_coverage": m3_sim_coverage,
    "m3_primiceri": m3_primiceri,
}


def run_case(case: Case, tables: Tables) -> CaseResult:
    fn = FUNCTIONS.get(case.function)
    if fn is None:
        return CaseResult(case, (), f"unknown case function '{case.function}'")
    start = time.perf_counter()
    try:
        observed = fn(tables, case.settings, case.seed)
    except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
        return CaseResult(case, (), f"{type(exc).__name__}: {exc}", time.perf_counter() - start)
    return evaluate(case, observed, time.perf_counter() - start)
