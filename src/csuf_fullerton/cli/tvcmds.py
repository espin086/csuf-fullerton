"""CLI commands for change 0005: trade-weights, tvsvar and replicate."""

from __future__ import annotations

import hashlib
import json
import tomllib
import urllib.error
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import typer

from csuf_fullerton.cli.main import _fail, _load, _write_run, app, console
from csuf_fullerton.core.replication.cases import Case, CaseResult, parse_case, registry_gaps
from csuf_fullerton.core.replication.run import run_case, trade_weights
from csuf_fullerton.core.tvsvar import m3
from csuf_fullerton.core.tvsvar.model import (
    MODELS,
    TvSettings,
    run_m0,
    run_m1,
    run_m2,
    run_m3,
)
from csuf_fullerton.core.tvsvar.report import m0_markdown, m1_markdown, m2_markdown, m3_markdown


def _pairs(text: str) -> tuple[tuple[str, str], ...]:
    """``"us=USA,cn=CHN"`` -> (("us", "USA"), ("cn", "CHN"))."""
    out = []
    for item in filter(None, (x.strip() for x in text.split(","))):
        if "=" not in item:
            raise _fail(f"expected name=value, got '{item}'", 2)
        a, b = item.split("=", 1)
        out.append((a.strip(), b.strip()))
    return tuple(out)


@app.command(name="trade-weights")
def trade_weights_cmd(
    country: str = typer.Option(..., "--country", help="IMF reporter code, e.g. BRA."),
    partners: str = typer.Option(..., "--partners", help="name=IMF code list, e.g. us=USA,cn=CHN"),
    out: Path = typer.Option(..., "--out", help="CSV of annual trade by partner to write."),
    world: str = typer.Option("G001", "--world", help="IMF code of the world total."),
) -> None:
    """Download annual goods exports plus imports by partner (IMF IMTS) for trade weights."""
    from csuf_fullerton.data.adapters import imf

    mapping = dict(_pairs(partners))
    try:
        rows = imf.fetch_rows("IMTS", {"COUNTRY": country, "FREQUENCY": "A"})
    except urllib.error.URLError as exc:
        raise _fail(f"IMF IMTS: {exc}", 4) from exc
    table = imf.trade_table(rows, mapping, world)
    if not table:
        raise _fail("no trade rows matched the partners", 4)
    df = pd.DataFrame(
        [
            {"year": y, "partner": p, "value": v}
            for (p, y), v in sorted(table.items(), key=lambda x: (x[0][1], x[0][0]))
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    meta = {
        "retrieved": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": "IMF IMTS, goods exports FOB plus imports CIF, U.S. dollars",
        "country": country,
        "partners": mapping,
        "world": world,
    }
    out.with_suffix(".sources.json").write_text(json.dumps(meta, indent=2))
    console.print(f"Wrote {out} ({df['year'].nunique()} years).")


def _headlines(text: str) -> tuple[tuple[str, str], ...]:
    out = []
    for item in filter(None, (x.strip() for x in text.split(","))):
        if ":" not in item:
            raise _fail(f"headline must be response:shock, got '{item}'", 2)
        a, b = item.split(":", 1)
        out.append((a, b))
    return tuple(out)


def _partner_cols(text: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple((p, tuple(c.split("+"))) for p, c in _pairs(text))


def _irf_csv(path: Path, names: tuple[str, ...], arrays: dict[str, np.ndarray]) -> None:
    recs: list[dict[str, Any]] = []
    first = next(iter(arrays.values()))
    hz, k, _ = first.shape
    for h in range(hz):
        for i in range(k):
            for j in range(k):
                row: dict[str, Any] = {"h": h, "response": names[i], "shock": names[j]}
                row |= {key: float(a[h, i, j]) for key, a in arrays.items()}
                recs.append(row)
    pd.DataFrame(recs).to_csv(path, index=False)


@app.command()
def tvsvar(
    data: Path = typer.Argument(..., exists=True, dir_okay=False),
    model: str = typer.Option("m1", "--model", help="m0, m1, m2 or m3"),
    foreign: str = typer.Option(..., "--foreign", help="Comma-separated foreign block, in order."),
    domestic: str = typer.Option(..., "--domestic", help="Comma-separated domestic block."),
    trade: Path | None = typer.Option(None, "--trade", help="CSV from `trade-weights`."),
    partners: str = typer.Option("", "--partners", help="partner=column(+column) list"),
    window: int = typer.Option(3, "--weight-window"),
    weights_lag: int = typer.Option(1, "--weights-lag"),
    variant: str = typer.Option("interacted", "--variant"),
    bands: str = typer.Option("hall", "--bands", help="hall or percentile"),
    lr_draws: int = typer.Option(199, "--lr-draws", help="Bootstrap draws for M1 LR tests."),
    frozen_years: str = typer.Option("", "--frozen-years", help="e.g. 2000,2009,2019"),
    headline: str = typer.Option("", "--headline", help="response:shock list"),
    lags: int | None = typer.Option(None, "--lags"),
    max_lags: int = typer.Option(6, "--max-lags"),
    trend: bool = typer.Option(True, "--trend/--no-trend"),
    seasonal: bool = typer.Option(False, "--seasonal/--no-seasonal"),
    horizon: int = typer.Option(24, "--horizon"),
    draws: int = typer.Option(500, "--draws"),
    level: float = typer.Option(0.68, "--level"),
    break_date: str | None = typer.Option(None, "--break"),
    break_draws: int = typer.Option(199, "--break-draws"),
    bandwidth_exp: float = typer.Option(0.5, "--bandwidth-exp"),
    kernel_step: int = typer.Option(1, "--kernel-step"),
    m3_vars: str = typer.Option("", "--m3-vars", help="Small system for M3, foreign first."),
    m3_lags: int = typer.Option(2, "--m3-lags"),
    m3_yoy: str = typer.Option("", "--m3-yoy", help="M3 columns to use as 12-month changes."),
    mcmc_draws: int = typer.Option(10000, "--mcmc-draws"),
    burn: int = typer.Option(2000, "--burn"),
    thin: int = typer.Option(4, "--thin"),
    training: int = typer.Option(0, "--training"),
    irf_dates: str = typer.Option("", "--irf-dates", help="M3 dates, e.g. 2002-06,2019-06"),
    seed: int = typer.Option(20261014, "--seed"),
    start: str | None = typer.Option(None, "--start"),
    end: str | None = typer.Option(None, "--end"),
    out: Path = typer.Option(Path("results/tvsvar"), "--out"),
) -> None:
    """Time-varying block-exogenous SVAR: M0 baseline and stability, M1 trade-weighted,
    M2 kernel, M3 TVP-VAR with stochastic volatility."""
    from csuf_fullerton.cli import plots, tvplots

    if model not in MODELS:
        raise _fail(f"--model must be one of {MODELS}", 2)
    s = TvSettings(
        tuple(foreign.split(",")),
        tuple(domestic.split(",")),
        _partner_cols(partners),
        lags,
        max_lags,
        trend,
        seasonal,
        horizon,
        draws,
        level,
        tuple(int(y) for y in frozen_years.split(",") if y),
        variant,
        bands,
        lr_draws,
        break_date,
        break_draws,
        bandwidth_exp,
        kernel_step,
        _headlines(headline),
        tuple(v for v in m3_vars.split(",") if v),
        0,
        tuple(v for v in m3_yoy.split(",") if v),
        m3.TvpSettings(p=m3_lags, draws=mcmc_draws, burn=burn, thin=thin, training=training),
        seed,
    )
    ds, digest = _load(data, start, end)
    tw = None
    trade_digest = None
    if trade is not None:
        tdf = pd.read_csv(trade)
        trade_digest = hashlib.sha256(trade.read_bytes()).hexdigest()
        try:
            tw = trade_weights(tdf, [p for p, _ in s.partners], window, weights_lag, ds.dates)
        except ValueError as exc:
            raise _fail(f"trade weights: {exc}", 2) from exc
    out.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "command": "tvsvar",
        "model": model,
        "data": str(data),
        "data_sha256": digest,
        "trade": None if trade is None else str(trade),
        "trade_sha256": trade_digest,
        "weight_window": window,
        "weights_lag": weights_lag,
        "settings": {k: v for k, v in s.__dict__.items() if k != "tvp"} | {"tvp": s.tvp.__dict__},
        "start": start,
        "end": end,
    }
    try:
        if model == "m0":
            r0 = run_m0(ds, s)
            figs = {"irf": plots.irf_grid(r0.svar, out)}
            (out / "m0.md").write_text(m0_markdown(r0, figs))
            _irf_csv(
                out / "irf.csv",
                r0.svar.names,
                {
                    "irf": r0.svar.bands.point,
                    "lower": r0.svar.bands.lower,
                    "upper": r0.svar.bands.upper,
                },
            )
            record |= {
                "p": r0.svar.fit.p,
                "sample": r0.svar.sample,
                "stability": [t.__dict__ for t in r0.stability],
                "sup_date": r0.sup_date,
            }
            report = out / "m0.md"
        elif model == "m1":
            if tw is None:
                raise _fail("M1 needs --trade", 2)
            r1 = run_m1(ds, tw, s)
            figs = tvplots.m1_figures(r1, out)
            (out / "m1.md").write_text(m1_markdown(r1, figs))
            b = r1.bands
            arrays: dict[str, np.ndarray] = {}
            for yi, yr in enumerate(b.years):
                arrays |= {
                    f"irf_{yr}": b.point[yi],
                    f"lower_{yr}": b.lower[yi],
                    f"upper_{yr}": b.upper[yi],
                }
            for di, yr in enumerate(b.years[1:]):
                arrays |= {
                    f"diff_{yr}_{b.years[0]}": b.diff_point[di],
                    f"diff_lower_{yr}_{b.years[0]}": b.diff_lower[di],
                    f"diff_upper_{yr}_{b.years[0]}": b.diff_upper[di],
                }
            _irf_csv(out / "irf.csv", r1.names, arrays)
            lp = pd.DataFrame({"date": r1.weight_dates})
            for j, pn in enumerate(r1.partners):
                lp[f"weight_{pn}"] = r1.weights[:, j]
            for key, path in r1.loading.items():
                lp[f"loading_{key.replace('|', '_on_')}"] = path
            lp.to_csv(out / "loading_path.csv", index=False)
            record |= {
                "p": r1.p,
                "sample": r1.sample,
                "frozen_weights": r1.frozen_weights,
                "tests": {
                    t.name: {
                        "stat": t.stat,
                        "df": t.df,
                        "p": t.pvalue,
                        "bootstrap_p": r1.bootstrap_p.get(t.name),
                    }
                    for t in r1.tests
                },
            }
            report = out / "m1.md"
        elif model == "m2":
            r2 = run_m2(ds, s, tw)
            figs = tvplots.m2_figure(r2, list(s.headlines), out, len(s.foreign))
            (out / "m2.md").write_text(m2_markdown(r2, figs))
            kp = pd.DataFrame({"date": r2.dates})
            for resp, shock in s.headlines:
                i, j = s.domestic.index(resp), s.foreign.index(shock)
                kp[f"loading_{resp}_on_{shock}"] = r2.path.impact[:, i, j]
                kp[f"se_{resp}_on_{shock}"] = r2.path.impact_se[:, i, j]
            kp.to_csv(out / "kernel_path.csv", index=False)
            record |= {"p": r2.p, "bandwidth": r2.bandwidth, "weight_corr": r2.weight_corr}
            report = out / "m2.md"
        else:
            dates = tuple(d for d in irf_dates.split(",") if d)
            r3 = run_m3(ds, s, dates)
            figs = tvplots.m3_figures(r3, list(s.headlines), out)
            (out / "m3.md").write_text(m3_markdown(r3, figs))
            vol = np.median(np.exp(r3.result.g / 2), axis=0)
            vdf = pd.DataFrame(vol, columns=[f"sd_{n}" for n in r3.names])
            vdf.insert(0, "date", r3.dates)
            vdf.to_csv(out / "m3_volatility.csv", index=False)
            arrays = {}
            for di, d in enumerate(r3.irf_dates):
                arrays |= {
                    f"median_{d}": np.median(r3.irfs[di], axis=0),
                    f"p16_{d}": np.quantile(r3.irfs[di], 0.16, axis=0),
                    f"p84_{d}": np.quantile(r3.irfs[di], 0.84, axis=0),
                }
            if arrays:
                _irf_csv(out / "irf.csv", r3.names, arrays)
            record |= {"sample": (r3.dates[0], r3.dates[-1]), "diagnostics": r3.diagnostics}
            report = out / "m3.md"
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise _fail(str(exc), 5) from exc
    _write_run(out, record)
    console.print(f"Report: {report}")


def _load_cases(folder: Path) -> list[Case]:
    cases = []
    for f in sorted(folder.glob("*.toml")):
        try:
            cases.append(parse_case(tomllib.loads(f.read_text())))
        except (ValueError, KeyError, tomllib.TOMLDecodeError) as exc:
            raise _fail(f"{f.name}: {exc}", 2) from exc
    ids = [c.id for c in cases]
    if len(set(ids)) != len(ids):
        raise _fail("duplicate case ids", 2)
    return cases


def _scorecard(results: list[CaseResult], out: Path) -> None:
    from csuf_fullerton.__about__ import __version__

    rows = []
    for r in results:
        for m in r.metrics:
            rows.append(
                {
                    "case": r.case.id,
                    "model": r.case.model,
                    "kind": r.case.kind,
                    "metric": m.metric.name,
                    "observed": m.observed,
                    "passed": m.passed,
                    "golden_passed": m.golden_passed,
                    "message": m.message,
                }
            )
        if r.error:
            rows.append(
                {
                    "case": r.case.id,
                    "model": r.case.model,
                    "kind": r.case.kind,
                    "metric": "",
                    "passed": False,
                    "message": r.error,
                }
            )
    import scipy
    import statsmodels

    card = {
        "package_version": __version__,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "versions": {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__,
            "pandas": pd.__version__,
        },
        "passed": all(r.passed for r in results),
        "cases": [
            {
                "id": r.case.id,
                "passed": r.passed,
                "seconds": round(r.seconds, 2),
                "seed": r.case.seed,
                "error": r.error,
            }
            for r in results
        ],
        "metrics": rows,
    }
    (out / "scorecard.json").write_text(json.dumps(card, indent=2, default=str))
    lines = [
        "# Replication scorecard",
        "",
        "| Case | Model | Kind | Result | Seconds |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        qual = " (qualitative)" if r.case.qualitative else ""
        lines.append(
            f"| {r.case.id} | {r.case.model} | {r.case.kind}{qual} "
            f"| {'pass' if r.passed else 'FAIL'} | {r.seconds:.1f} |"
        )
    lines += ["", "## Metrics", ""]
    for r in results:
        lines.append(f"**{r.case.id}** ({r.case.source})")
        lines.append("")
        if r.error:
            lines.append(f"- error: {r.error}")
        for m in r.metrics:
            flag = "pass" if m.passed and m.golden_passed is not False else "FAIL"
            lines.append(f"- {flag}: {m.message}")
        lines.append("")
    (out / "replication.md").write_text("\n".join(lines) + "\n")


@app.command()
def replicate(
    suite: str = typer.Option("fast", "--suite", help="fast, full, or all"),
    cases_dir: Path = typer.Option(Path("replication/cases"), "--cases"),
    only: list[str] = typer.Option([], "--case", help="Run only these case ids."),
    list_cases: bool = typer.Option(False, "--list", help="List cases and check the registry."),
    root: Path = typer.Option(Path("."), "--root", help="Repo root that data paths resolve from."),
    out: Path = typer.Option(Path("results/replication"), "--out"),
) -> None:
    """Run the replication suite: simulation, parity and published-result cases."""
    cases = _load_cases(cases_dir)
    gaps = registry_gaps(cases)
    if list_cases:
        for c in cases:
            console.print(f"{c.id:<36} {c.model}  {c.kind:<11} {c.suite}")
        if gaps:
            raise _fail(f"registry incomplete: {gaps}", 1)
        return
    if gaps:
        raise _fail(f"registry incomplete: {gaps}", 1)
    chosen = [
        c
        for c in cases
        if (suite == "all" or c.suite == suite or (suite == "full" and c.suite == "fast"))
        and (not only or c.id in only)
    ]
    if not chosen:
        raise _fail("no cases selected", 2)
    results: list[CaseResult] = []
    for c in chosen:
        tables = {}
        bad = ""
        for d in c.data:
            path = root / d.path
            if not path.exists():
                bad = f"fixture missing: {d.path}"
                break
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != d.sha256:
                bad = f"fixture hash mismatch: {d.path} is {digest[:12]}, case pins {d.sha256[:12]}"
                break
            tables[d.name] = pd.read_csv(path)
        r = CaseResult(c, (), bad) if bad else run_case(c, tables)
        results.append(r)
        console.print(f"  {'pass' if r.passed else 'FAIL'}  {c.id}  ({r.seconds:.1f}s)")
        if r.error:
            console.print(f"        {r.error}")
        for m in r.metrics:
            if not m.passed or m.golden_passed is False:
                console.print(f"        {m.message}")
    out.mkdir(parents=True, exist_ok=True)
    _scorecard(results, out)
    failed = [r.case.id for r in results if not r.passed]
    console.print(
        f"{len(results) - len(failed)} of {len(results)} cases passed. "
        f"Scorecard: {out / 'scorecard.json'}"
    )
    if failed:
        raise typer.Exit(code=1)
