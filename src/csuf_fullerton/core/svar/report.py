"""Markdown text for screening and SVAR results. Pure string building, no file access."""

from __future__ import annotations

from collections.abc import Mapping

from csuf_fullerton.core.svar.model import SvarResult
from csuf_fullerton.core.svar.screening import CandidateResult, ScreenResult


def _p(x: float) -> str:
    return "<0.001" if x < 0.001 else f"{x:.3f}"


def _table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def _fig(figures: Mapping[str, str], key: str, alt: str) -> str:
    return f"\n![{alt}]({figures[key]})\n" if key in figures else ""


def candidate_rows(cands: list[CandidateResult]) -> list[list[str]]:
    rows = []
    for c in cands:
        crit = c.crit
        rows.append(
            [
                str(c.rank or "-"),
                "{" + ", ".join(c.spec.foreign) + "}",
                c.grade,
                c.verdict or "-",
                _p(c.wald_p_asym),
                _p(c.wald.pvalue),
                _p(c.wald_p_adj),
                _p(c.lr.pvalue),
                _p(c.inst.pvalue) if c.inst else "-",
                ", ".join(c.weak_rejected) or "none",
                _p(c.cw_p_adj_min),
                f"{crit.bic:.3f}" if crit else "-",
                f"{c.lingam_agreement:.2f} ({c.lingam_agreement_lo:.2f})",
                f"{c.root:.3f}",
            ]
        )
    return rows


CANDIDATE_HEADER = [
    "Rank",
    "Foreign block",
    "Theory",
    "Verdict",
    "LA-Wald asym. p",
    "LA-Wald boot p",
    "Holm p",
    "LR p",
    "Inst. p",
    "Not weakly exog.",
    "CW Holm p",
    "BIC",
    "LiNGAM agree (5%)",
    "Max root",
]


def screen_markdown(r: ScreenResult, figures: Mapping[str, str] | None = None) -> str:
    figs = figures or {}
    th = r.theory
    names = th.names
    rec = r.recommended
    lines = [f"# Exogeneity screen: {th.country or 'dataset'}", ""]
    lines += [
        f"Sample {r.sample[0]} to {r.sample[1]}, {r.nobs} effective observations, "
        f"{len(names)} variables, lag order p = {r.p} "
        f"(AIC {r.lag_choice['aic']}, BIC {r.lag_choice['bic']}, HQ {r.lag_choice['hq']}), "
        f"lag augmentation d_max = {r.dmax}. Deterministic terms: constant"
        + (", trend" if th.trend else "")
        + (", seasonal dummies" if th.seasonal else "")
        + ".",
        "",
    ]
    if rec is not None:
        lines += [
            "## Recommendation",
            "",
            f"**Foreign block {{{', '.join(rec.spec.foreign)}}}**, domestic block "
            f"{{{', '.join(rec.spec.domestic)}}}. Theory grade {rec.grade} "
            f"({rec.grade_reason}); statistical verdict **{rec.verdict}** "
            f"({rec.verdict_reason}).",
            "",
        ]
        ranked = r.ranked
        if len(ranked) > 1:
            ru = ranked[1]
            lines += [
                f"Runner-up: {{{', '.join(ru.spec.foreign)}}}, grade {ru.grade}, verdict "
                f"{ru.verdict}, BIC {ru.crit.bic if ru.crit else float('nan'):.3f} against "
                f"{rec.crit.bic if rec.crit else float('nan'):.3f}.",
                "",
            ]
    lines += ["## Stage 1. Integration order", ""]
    lines.append(
        _table(
            [
                "Variable",
                "Order",
                "ADF p (level)",
                "KPSS p (level)",
                "ADF p (diff)",
                "KPSS p (diff)",
                "Conflict",
            ],
            [
                [
                    o.name,
                    f"I({o.order})",
                    _p(o.adf_p_level),
                    _p(o.kpss_p_level),
                    _p(o.adf_p_diff),
                    _p(o.kpss_p_diff),
                    "yes" if o.conflict else "",
                ]
                for o in r.orders
            ],
        )
    )
    j = r.johansen
    lines += [
        "",
        f"Johansen trace test: cointegrating rank {j.rank} of {len(names)} at 5%. "
        + (
            "Weak exogeneity tests are run on the foreign block."
            if 0 < j.rank < len(names) and r.dmax > 0
            else "Weak exogeneity tests do not apply (rank 0, full rank, or stationary data)."
        ),
        "",
        "## Stage 3. Pairwise evidence",
        "",
        "Lag-augmented (Toda-Yamamoto) Granger p-values, conditional on the whole system, "
        "unadjusted. Row is the equation (effect), column the cause. Bold marks pairs that stay "
        f"below {r.config.alpha} after Holm adjustment across all "
        f"{len(names) * (len(names) - 1)} pairs.",
        "",
    ]
    rows = []
    for i, n in enumerate(names):
        row = [n]
        for jj in range(len(names)):
            if i == jj:
                row.append("")
            else:
                v = _p(float(r.granger_p[i, jj]))
                row.append(f"**{v}**" if r.granger_p_adj[i, jj] < r.config.alpha else v)
        rows.append(row)
    lines.append(_table(["effect \\ cause", *names], rows))
    lines.append(_fig(figs, "granger", "Granger heat map"))
    co = r.causal_order
    lines += [
        "",
        "DirectLiNGAM causal order of the reduced-form residuals (advisory; needs "
        f"non-Gaussian residuals, {co.nongaussian_share:.0%} of series reject normality): "
        f"**{' > '.join(co.order)}**.",
        "",
    ]
    ident = [d for d in r.directions if d.identified]
    if ident:
        lines.append(
            _table(
                ["Pair", "Pairwise direction", "R"],
                [[f"{d.cause}, {d.effect}", d.verdict, f"{d.r:+.4f}"] for d in ident],
            )
        )
        lines.append("")
    lines += [
        "## Stage 4 and 5. Candidate specifications",
        "",
        "LA-Wald is the primary test (domestic lags excluded from foreign equations, robust to "
        + "unit roots); its p-value is bootstrapped under the null (Hacker and Hatemi-J 2006) "
        + "because the asymptotic version over-rejects in samples this size. Holm p adjusts the "
        + "bootstrap p across every admissible candidate. LR is the Sims-"
        + "corrected likelihood ratio of change 0002. Inst. p tests residual correlation between "
        + "blocks (rejection is expected and is what the recursive impact matrix orders). CW is "
        + "the Clark-West out-of-sample test that domestic lags improve foreign forecasts. LiNGAM "
        + "agree is the share of foreign-domestic pairs the data-driven causal order puts foreign "
        + "first, with the bootstrap 5th percentile.",
        "",
        _table(CANDIDATE_HEADER, candidate_rows(sorted(r.candidates, key=lambda c: c.rank or 999))),
        "",
    ]
    bad = [c for c in r.candidates if c.grade == "X"]
    if bad:
        lines += [
            "Inadmissible by theory (not ranked): "
            + "; ".join(f"{{{', '.join(c.spec.foreign)}}} ({c.grade_reason})" for c in bad),
            "",
        ]
    lines += ["## Stage 6. Robustness of headline responses", ""]
    for rob in r.robustness:
        lines.append(
            f"- **{rob.headline.response} to a {rob.headline.shock} shock**: recommended "
            f"specification peaks at {rob.recommended_peak:+.4f} at horizon "
            f"{rob.recommended_peak_h}; {rob.same_sign} of {rob.total} surviving specifications "
            "and orderings have the same sign there."
        )
        lines.append(
            _fig(figs, f"robust_{rob.headline.response}_{rob.headline.shock}", "robustness")
        )
    lines += ["", "## Theory file", ""]
    lines.append(
        _table(
            ["Variable", "Prior", "Rationale", "Source"],
            [[v.name, v.prior, v.rationale, v.source] for v in th.variables],
        )
    )
    return "\n".join(lines) + "\n"


def svar_markdown(r: SvarResult, figures: Mapping[str, str] | None = None) -> str:
    figs = figures or {}
    s = r.settings
    lines = [
        "# Block-exogenous SVAR",
        "",
        f"Foreign block {{{', '.join(s.foreign)}}}, domestic block {{{', '.join(s.domestic)}}}. "
        f"Sample {r.sample[0]} to {r.sample[1]} ({r.fit.nobs} observations), p = {r.fit.p}, "
        f"recursive identification in the order listed, {s.draws} bootstrap draws, "
        f"{s.level:.0%} {s.band_method} bands.",
        "",
        _table(
            ["Test", "Statistic", "df", "p"],
            [
                [t.name, f"{t.stat:.2f}", str(t.df), _p(t.pvalue)]
                for t in (r.lr, r.wald, r.resid_check)
            ]
            + [["max companion root", f"{r.root:.3f}", "", ""]],
        ),
        "",
    ]
    if r.restriction_rejected:
        lines += [
            "**Warning:** the block-exogeneity restriction is rejected at 5% "
            f"(LR p = {_p(r.lr.pvalue)}, lag-augmented Wald p = {_p(r.wald.pvalue)}). It is "
            "still imposed. With integrated data the levels LR test over-rejects; the "
            "lag-augmented Wald is the valid test (see the exogeneity screen).",
            "",
        ]
    lines.append(_fig(figs, "irf", "impulse responses"))
    h_rows = [h for h in (0, 6, 12, 24) if h < r.fevd.shape[0]]
    lines += ["## Forecast error variance decomposition", ""]
    for i, n in enumerate(r.names[len(s.foreign) :], start=len(s.foreign)):
        lines.append(f"**{n}**")
        lines.append("")
        lines.append(
            _table(
                ["h", *r.names],
                [[str(h)] + [f"{100 * v:.1f}" for v in r.fevd[h, i]] for h in h_rows],
            )
        )
        lines.append("")
    foreign_share = r.fevd[-1, len(s.foreign) :, : len(s.foreign)].sum(axis=1)
    lines.append(
        "Share of domestic forecast error variance due to foreign shocks at the last horizon: "
        + ", ".join(
            f"{n} {100 * v:.1f}%"
            for n, v in zip(r.names[len(s.foreign) :], foreign_share, strict=True)
        )
        + "."
    )
    return "\n".join(lines) + "\n"
