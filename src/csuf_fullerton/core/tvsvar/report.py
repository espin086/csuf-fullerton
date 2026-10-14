"""Markdown reports for the time-varying SVAR runs. Pure: strings from result objects."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from csuf_fullerton.core.svar.report import _fig, _p, _table, svar_markdown
from csuf_fullerton.core.tvsvar.model import M0Result, M1Result, M2Result, M3Result


def _h_rows(n: int) -> list[int]:
    return [h for h in (0, 3, 6, 12, 24) if h < n]


def m0_markdown(r: M0Result, figures: Mapping[str, str] | None = None) -> str:
    lines = [svar_markdown(r.svar, figures).rstrip(), "", "## Parameter stability", ""]
    rows = []
    for t in r.stability:
        where = r.break_date if t.name.startswith("Chow") else r.sup_date
        asym = "" if t.asymptotic_p is None else _p(t.asymptotic_p)
        rows.append([t.name, where or "", f"{t.stat:.1f}", str(t.df), asym, _p(t.bootstrap_p)])
    lines.append(
        _table(
            ["Test", "Break", "LR", "df", "chi2 p", f"bootstrap p ({r.stability[0].draws})"], rows
        )
    )
    lines += [
        "",
        "Bootstrap p-values come from the constant-coefficient fit, so they test the null of "
        "no break at any date in the trimmed range (sup-LR) or at the chosen date (Chow).",
    ]
    return "\n".join(lines) + "\n"


def m1_markdown(r: M1Result, figures: Mapping[str, str] | None = None) -> str:
    figs = figures or {}
    b = r.bands
    names = r.names
    lines = [
        "# Trade-weighted block-exogenous SVAR (M1)",
        "",
        f"Variant **{r.variant}**, sample {r.sample[0]} to {r.sample[1]} "
        f"({r.fits[r.variant].nobs} observations), p = {r.p}. Weights are "
        f"{r.weight_window}-year moving averages of each partner's share of exports plus "
        f"imports, lagged {r.weight_lag} year(s). Impulse responses hold the weights at the "
        f"values of each frozen year; {b.draws} bootstrap draws with the observed weight path, "
        f"{b.level:.0%} Hall bands; differences are formed draw by draw.",
        "",
        "## Frozen weights",
        "",
        _table(
            ["Year", *r.partners],
            [[str(y), *[f"{v:.3f}" for v in w]] for y, w in r.frozen_weights.items()],
        ),
        "",
        "## Is the time variation real?",
        "",
        _table(
            ["Test", "Statistic", "df", "chi2 p", "bootstrap p"],
            [
                [
                    t.name,
                    f"{t.stat:.2f}",
                    str(t.df),
                    _p(t.pvalue),
                    _p(r.bootstrap_p[t.name]) if t.name in r.bootstrap_p else "",
                ]
                for t in r.tests
            ],
        ),
        "",
        "Bootstrap p-values regenerate the data from the restricted model along the observed "
        "weight path and re-estimate both models on every draw, so they do not rely on the "
        "chi-square limit, which can over-reject with persistent regressors.",
        "",
    ]
    lines.append(_fig(figs, "frozen", "frozen-weight impulse responses"))
    lines.append(_fig(figs, "diff", "differences between frozen years"))
    lines.append(_fig(figs, "loading", "impact loading over the sample"))
    lines += ["", "## Headline responses by frozen year", ""]
    rows = []
    for key in r.loading:
        resp, shock = key.split("|")
        i, j = names.index(resp), names.index(shock)
        for h in _h_rows(b.point.shape[1]):
            row = [f"{resp} to {shock}", str(h)]
            for yi in range(len(b.years)):
                row.append(
                    f"{b.point[yi, h, i, j]:+.3f} [{b.lower[yi, h, i, j]:+.3f}, "
                    f"{b.upper[yi, h, i, j]:+.3f}]"
                )
            for di in range(len(b.years) - 1):
                lo, hi = b.diff_lower[di, h, i, j], b.diff_upper[di, h, i, j]
                mark = " *" if lo > 0 or hi < 0 else ""
                row.append(f"{b.diff_point[di, h, i, j]:+.3f} [{lo:+.3f}, {hi:+.3f}]{mark}")
            rows.append(row)
    head = ["Response", "h", *[str(y) for y in b.years]]
    head += [f"{y} minus {b.years[0]}" for y in b.years[1:]]
    if rows:
        lines.append(_table(head, rows))
        lines += ["", "`*` marks a difference whose band excludes zero.", ""]
    return "\n".join(lines) + "\n"


def m2_markdown(r: M2Result, figures: Mapping[str, str] | None = None) -> str:
    figs = figures or {}
    bw = "flat (constant model)" if np.isinf(r.bandwidth) else f"{r.bandwidth:.1f} months"
    lines = [
        "# Kernel time-varying block SVAR (M2)",
        "",
        f"Gaussian kernel, bandwidth {bw}, p = {r.p}, local estimates at "
        f"{len(r.dates)} dates from {r.dates[0]} to {r.dates[-1]}. Bands on impact loadings "
        "are pointwise 90% intervals from the sandwich variance.",
        "",
    ]
    if r.weight_corr:
        lines.append(
            _table(
                ["Loading", "Correlation with the partner's trade weight"],
                [[k.replace("|", " on "), f"{v:+.2f}"] for k, v in r.weight_corr.items()],
            )
        )
        lines.append("")
    lines.append(_fig(figs, "kernel", "kernel impact loadings"))
    return "\n".join(lines) + "\n"


def m3_markdown(r: M3Result, figures: Mapping[str, str] | None = None) -> str:
    figs = figures or {}
    s = r.result.settings
    lines = [
        "# TVP-VAR with stochastic volatility (M3)",
        "",
        f"Variables {', '.join(r.names)} (first {r.result.layout.nf} foreign"
        + (f"; {', '.join(r.diff12)} as 12-month changes" if r.diff12 else "")
        + f"), p = {s.p}, "
        f"sample {r.dates[0]} to {r.dates[-1]}. {s.draws} Gibbs iterations, burn-in {s.burn}, "
        f"thinning {s.thin}, {r.result.accepted_draws} kept draws, seed {s.seed}. Priors: "
        f"k_Q = {s.k_q}, k_S = {s.k_s}, k_W = {s.k_w}, "
        + (
            f"OLS training sample of {s.training} observations."
            if r.result.prior_from_training
            else "centred on full-sample OLS (no training sample; this makes the prior "
            "data-dependent and is a known weakness in short samples)."
        ),
        "",
        "## MCMC diagnostics",
        "",
        _table(
            ["Block", "median inefficiency", "max inefficiency", "max |Geweke z|"],
            [
                [
                    k,
                    f"{v['median_inefficiency']:.1f}",
                    f"{v['max_inefficiency']:.1f}",
                    f"{v['max_abs_geweke_z']:.2f}",
                ]
                for k, v in r.diagnostics.items()
            ],
        ),
        "",
    ]
    lines.append(_fig(figs, "vol", "posterior median structural volatilities"))
    lines.append(_fig(figs, "m3irf", "impulse responses by date"))
    return "\n".join(lines) + "\n"
