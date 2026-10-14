"""Command-line entry point."""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import typer
from rich.console import Console

from csuf_fullerton.__about__ import __version__
from csuf_fullerton.core.greeting import greet
from csuf_fullerton.core.recipe import assemble, parse_recipe
from csuf_fullerton.core.svar.data import Dataset, make_dataset
from csuf_fullerton.core.svar.model import SvarSettings, estimate_svar
from csuf_fullerton.core.svar.report import screen_markdown, svar_markdown
from csuf_fullerton.core.svar.screening import ScreenConfig, screen
from csuf_fullerton.core.svar.theory import parse_theory

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        # Plain print: machine-readable, no Rich number colouring under FORCE_COLOR.
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Print the version and exit.",
    ),
) -> None:
    """csuf-fullerton command line."""


@app.command()
def hello(name: str = typer.Argument("world", help="Who to greet.")) -> None:
    """Print a greeting. Example command; replace with real ones."""
    try:
        console.print(greet(name))
    except ValueError as exc:
        console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=2) from exc


def _fail(msg: str, code: int) -> typer.Exit:
    console.print(f"[red]error:[/red] {msg}")
    return typer.Exit(code=code)


@app.command()
def init(
    file: bool = typer.Option(
        False, "--file", help="Store in a 0600 file instead of the keychain."
    ),
    check: bool = typer.Option(False, "--check", help="Make one FRED request to verify the key."),
) -> None:
    """Store a FRED API key securely (OS keychain, or a 0600 file as fallback)."""
    from csuf_fullerton.data import credentials

    key = typer.prompt("FRED API key", hide_input=True).strip()
    if not credentials.valid_key(key):
        raise _fail("a FRED API key is 32 lower-case letters and digits", 2)
    if check:
        from csuf_fullerton.data.adapters import fred

        try:
            fred.fetch_series("FEDFUNDS", key)
        except urllib.error.HTTPError as exc:
            raise _fail(f"FRED rejected the key (HTTP {exc.code})", 3) from exc
    where = credentials.store_fred_key(key, prefer_file=file)
    console.print(f"FRED API key stored in {'the OS keychain' if where == 'keyring' else where}.")
    if os.environ.get(credentials.ENV_VAR):
        console.print(
            f"Note: {credentials.ENV_VAR} is set and takes precedence over the stored key."
        )


@app.command()
def fetch(
    recipe: Path = typer.Argument(..., exists=True, dir_okay=False, help="TOML data recipe."),
    out: Path = typer.Option(..., "--out", help="CSV to write."),
) -> None:
    """Download FRED and IMF series from a recipe into one aligned CSV."""
    from csuf_fullerton.data import credentials
    from csuf_fullerton.data.adapters import fred, imf

    try:
        rec = parse_recipe(tomllib.loads(recipe.read_text()))
    except (ValueError, KeyError, tomllib.TOMLDecodeError) as exc:
        raise _fail(f"recipe: {exc}", 2) from exc
    key, _ = credentials.get_fred_key()
    if key is None:
        console.print(
            "No FRED API key found; using the keyless fredgraph CSV. Run `init` to add one."
        )
    raw: dict[str, dict[str, float]] = {}
    sources = []
    for s in rec.series:
        try:
            if s.source == "fred":
                raw[s.name] = fred.fetch_series(s.series_id, key, rec.frequency)
                ident = s.series_id
            else:
                raw[s.name] = imf.fetch_series(s.dataflow, s.filters)
                ident = f"{s.dataflow} {dict(s.filters)}"
        except (urllib.error.URLError, ValueError) as exc:
            raise _fail(f"{s.name}: {exc}", 4) from exc
        console.print(f"  {s.name:<12} {s.source}:{ident}  {len(raw[s.name])} obs")
        sources.append(
            {
                "name": s.name,
                "source": s.source,
                "id": ident,
                "transform": s.transform,
                "scale": s.scale,
                "description": s.description,
            }
        )
    dates, rows = assemble(rec, raw)
    df = pd.DataFrame(rows, columns=[s.name for s in rec.series])
    df.insert(0, "date", dates)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    meta = {
        "retrieved": datetime.now(UTC).isoformat(timespec="seconds"),
        "fred_access": "api" if key else "fredgraph",
        "series": sources,
    }
    out.with_suffix(".sources.json").write_text(json.dumps(meta, indent=2))
    console.print(f"Wrote {out} ({len(df)} rows) and {out.with_suffix('.sources.json').name}.")


def _load(csv: Path, start: str | None, end: str | None) -> tuple[Dataset, str]:
    raw = csv.read_bytes()
    df = pd.read_csv(csv)
    if "date" not in df.columns:
        raise _fail("CSV needs a 'date' column", 2)
    df["date"] = df["date"].astype(str)
    if start:
        df = df[df["date"] >= start]
    if end:
        df = df[df["date"] <= end]
    names = [c for c in df.columns if c != "date"]
    months = pd.to_datetime(df["date"]).dt.month.to_numpy()
    ds = make_dataset(names, df[names].to_numpy(float), df["date"].tolist(), months.tolist(), 12)
    return ds, hashlib.sha256(raw).hexdigest()


def _write_run(out: Path, record: dict[str, object]) -> None:
    record |= {
        "package_version": __version__,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out / "run.json").write_text(json.dumps(record, indent=2, default=str))


@app.command(name="screen")
def screen_cmd(
    data: Path = typer.Argument(..., exists=True, dir_okay=False, help="CSV with a date column."),
    theory: Path = typer.Argument(..., exists=True, dir_okay=False, help="TOML theory file."),
    out: Path = typer.Option(Path("results/screen"), "--out"),
    lags: int | None = typer.Option(None, "--lags", help="Override the lag order."),
    max_lags: int = typer.Option(6, "--max-lags"),
    alpha: float = typer.Option(0.05, "--alpha"),
    horizon: int = typer.Option(24, "--horizon"),
    dmax: int | None = typer.Option(None, "--dmax", help="Override lag augmentation."),
    start: str | None = typer.Option(None, "--start"),
    end: str | None = typer.Option(None, "--end"),
) -> None:
    """Grade candidate foreign/domestic splits on theory and statistics before the SVAR."""
    from csuf_fullerton.cli import plots

    try:
        th = parse_theory(tomllib.loads(theory.read_text()))
    except (ValueError, KeyError, tomllib.TOMLDecodeError) as exc:
        raise _fail(f"theory file: {exc}", 2) from exc
    ds, digest = _load(data, start, end)
    missing = [n for n in th.names if n not in ds.names]
    if missing:
        raise _fail(f"theory variables missing from data: {', '.join(missing)}", 2)
    cfg = ScreenConfig(alpha=alpha, max_lags=max_lags, lags=lags, horizon=horizon, dmax=dmax)
    try:
        res = screen(ds.select(th.names), th, cfg)
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise _fail(str(exc), 5) from exc
    out.mkdir(parents=True, exist_ok=True)
    figs = {"granger": plots.granger_heatmap(res, out)} | plots.robustness_plot(res, out)
    (out / "screen.md").write_text(screen_markdown(res, figs))
    rows = []
    for c in res.candidates:
        rows.append(
            {
                "rank": c.rank,
                "foreign": " ".join(c.spec.foreign),
                "domestic": " ".join(c.spec.domestic),
                "theory_grade": c.grade,
                "verdict": c.verdict,
                "la_wald_p": c.wald.pvalue,
                "la_wald_holm_p": c.wald_p_adj,
                "lr_p": c.lr.pvalue,
                "inst_p": c.inst.pvalue if c.inst else None,
                "not_weakly_exogenous": " ".join(c.weak_rejected),
                "clark_west_holm_p": c.cw_p_adj_min,
                "bic": c.crit.bic if c.crit else None,
                "aic": c.crit.aic if c.crit else None,
                "lingam_agreement": c.lingam_agreement,
                "max_root": c.root,
            }
        )
    pd.DataFrame(rows).sort_values("rank").to_csv(out / "candidates.csv", index=False)
    rec = res.recommended
    _write_run(
        out,
        {
            "command": "screen",
            "data": str(data),
            "data_sha256": digest,
            "theory": str(theory),
            "config": cfg.__dict__,
            "p": res.p,
            "dmax": res.dmax,
            "sample": res.sample,
            "recommended": (
                None
                if rec is None
                else {"foreign": rec.spec.foreign, "domestic": rec.spec.domestic}
            ),
        },
    )
    if rec is not None:
        console.print(
            f"Recommended foreign block: {', '.join(rec.spec.foreign)} "
            f"(theory {rec.grade}, {rec.verdict})."
        )
    console.print(f"Report: {out / 'screen.md'}")


@app.command()
def svar(
    data: Path = typer.Argument(..., exists=True, dir_okay=False),
    foreign: str = typer.Option(..., "--foreign", help="Comma-separated foreign block, in order."),
    domestic: str = typer.Option(..., "--domestic", help="Comma-separated domestic block."),
    lags: int | None = typer.Option(None, "--lags"),
    trend: bool = typer.Option(True, "--trend/--no-trend"),
    seasonal: bool = typer.Option(False, "--seasonal/--no-seasonal"),
    horizon: int = typer.Option(24, "--horizon"),
    draws: int = typer.Option(500, "--draws"),
    level: float = typer.Option(0.68, "--level"),
    bands: str = typer.Option("percentile", "--bands", help="percentile or hall"),
    dmax: int = typer.Option(1, "--dmax"),
    seed: int = typer.Option(20261014, "--seed"),
    start: str | None = typer.Option(None, "--start"),
    end: str | None = typer.Option(None, "--end"),
    out: Path = typer.Option(Path("results/svar"), "--out"),
) -> None:
    """Estimate a block-exogenous SVAR with bootstrap impulse responses."""
    from csuf_fullerton.cli import plots

    settings = SvarSettings(
        tuple(foreign.split(",")),
        tuple(domestic.split(",")),
        lags,
        trend=trend,
        seasonal=seasonal,
        horizon=horizon,
        draws=draws,
        level=level,
        band_method=bands,
        dmax=dmax,
        seed=seed,
    )
    ds, digest = _load(data, start, end)
    try:
        res = estimate_svar(ds, settings)
    except ValueError as exc:
        raise _fail(str(exc), 2 if "columns" in str(exc) or "both" in str(exc) else 5) from exc
    out.mkdir(parents=True, exist_ok=True)
    figs = {"irf": plots.irf_grid(res, out)}
    (out / "svar.md").write_text(svar_markdown(res, figs))
    h, k, _ = res.bands.point.shape
    recs = [
        {
            "h": t,
            "response": res.names[i],
            "shock": res.names[j],
            "irf": res.bands.point[t, i, j],
            "lower": res.bands.lower[t, i, j],
            "upper": res.bands.upper[t, i, j],
            "fevd": res.fevd[t, i, j],
        }
        for t in range(h)
        for i in range(k)
        for j in range(k)
    ]
    pd.DataFrame(recs).to_csv(out / "irf.csv", index=False)
    _write_run(
        out,
        {
            "command": "svar",
            "data": str(data),
            "data_sha256": digest,
            "settings": settings.__dict__,
            "p": res.fit.p,
            "sample": res.sample,
            "lag_criteria": res.lag_choice,
            "tests": {
                t.name: {"stat": t.stat, "df": t.df, "p": t.pvalue}
                for t in (res.lr, res.wald, res.resid_check)
            },
        },
    )
    if res.restriction_rejected:
        console.print(
            f"[yellow]warning:[/yellow] block exogeneity rejected "
            f"(LR p = {res.lr.pvalue:.3g}, Wald p = {res.wald.pvalue:.3g}); still imposed."
        )
    console.print(f"Report: {out / 'svar.md'}")


# Change 0005 commands register themselves on ``app``; imported last to avoid a cycle.
from csuf_fullerton.cli import tvcmds  # noqa: E402, F401

if __name__ == "__main__":
    app()
