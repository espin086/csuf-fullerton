"""Matplotlib figures for the time-varying SVAR runs. Returns the file names written."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from csuf_fullerton.core.tvsvar.model import M1Result, M2Result, M3Result

COLORS = ("#8d99ae", "#2a6f97", "#c1121f", "#588157")


def _pairs(keys: list[str]) -> list[tuple[str, str]]:
    return [(k.split("|")[0], k.split("|")[1]) for k in keys]


def _save(fig: Figure, out: Path, name: str) -> str:
    fig.tight_layout()
    fig.savefig(out / name, dpi=150)
    plt.close(fig)
    return name


def m1_figures(r: M1Result, out: Path) -> dict[str, str]:
    pairs = _pairs(list(r.loading))
    if not pairs:
        return {}
    b, names = r.bands, r.names
    h = np.arange(b.point.shape[1])
    files: dict[str, str] = {}
    fig, axes = plt.subplots(1, len(pairs), figsize=(4 * len(pairs), 3.2), squeeze=False)
    for ax, (resp, shock) in zip(axes[0], pairs, strict=True):
        i, j = names.index(resp), names.index(shock)
        for yi, yr in enumerate(b.years):
            c = COLORS[yi % len(COLORS)]
            ax.plot(h, b.point[yi, :, i, j], color=c, label=str(yr))
            ax.fill_between(h, b.lower[yi, :, i, j], b.upper[yi, :, i, j], color=c, alpha=0.15)
        ax.axhline(0, color="black", lw=0.5)
        ax.set_title(f"{resp} to {shock}", fontsize=9)
        ax.set_xlabel("months")
    axes[0][0].legend(fontsize=7, title="weights of")
    files["frozen"] = _save(fig, out, "frozen_irf.png")
    fig, axes = plt.subplots(1, len(pairs), figsize=(4 * len(pairs), 3.2), squeeze=False)
    for ax, (resp, shock) in zip(axes[0], pairs, strict=True):
        i, j = names.index(resp), names.index(shock)
        for di, yr in enumerate(b.years[1:]):
            c = COLORS[(di + 1) % len(COLORS)]
            ax.plot(h, b.diff_point[di, :, i, j], color=c, label=f"{yr} - {b.years[0]}")
            ax.fill_between(
                h, b.diff_lower[di, :, i, j], b.diff_upper[di, :, i, j], color=c, alpha=0.15
            )
        ax.axhline(0, color="black", lw=0.5)
        ax.set_title(f"change in {resp} to {shock}", fontsize=9)
        ax.set_xlabel("months")
    axes[0][0].legend(fontsize=7)
    files["diff"] = _save(fig, out, "frozen_diff.png")
    fig, ax = plt.subplots(figsize=(7, 3.2))
    x = np.arange(len(r.weight_dates))
    for n, (resp, shock) in enumerate(pairs):
        ax.plot(
            x, r.loading[f"{resp}|{shock}"], color=COLORS[(n + 1) % 4], label=f"{resp} on {shock}"
        )
    ax.set_ylabel("impact loading")
    ax2 = ax.twinx()
    for j, p in enumerate(r.partners):
        ax2.plot(x, r.weights[:, j], ls="--", color=COLORS[j % 4], lw=0.8, label=f"weight {p}")
    ax2.set_ylabel("trade weight")
    ticks = x[:: max(1, len(x) // 6)]
    ax.set_xticks(ticks, [r.weight_dates[t] for t in ticks], fontsize=7)
    ax.legend(fontsize=7, loc="upper left")
    ax2.legend(fontsize=7, loc="lower right")
    files["loading"] = _save(fig, out, "loading_path.png")
    return files


def m2_figure(r: M2Result, pairs: list[tuple[str, str]], out: Path, nf: int) -> dict[str, str]:
    if not pairs:
        return {}
    fig, ax = plt.subplots(figsize=(7, 3.2))
    x = np.arange(len(r.dates))
    for n, (resp, shock) in enumerate(pairs):
        i, j = r.names.index(resp) - nf, r.names.index(shock)
        m, se = r.path.impact[:, i, j], r.path.impact_se[:, i, j]
        c = COLORS[(n + 1) % 4]
        ax.plot(x, m, color=c, label=f"{resp} on {shock}")
        ax.fill_between(x, m - 1.645 * se, m + 1.645 * se, color=c, alpha=0.15)
    ax.axhline(0, color="black", lw=0.5)
    ticks = x[:: max(1, len(x) // 6)]
    ax.set_xticks(ticks, [r.dates[t] for t in ticks], fontsize=7)
    ax.set_ylabel("local impact loading")
    ax.legend(fontsize=7)
    return {"kernel": _save(fig, out, "kernel_loading.png")}


def m3_figures(r: M3Result, pairs: list[tuple[str, str]], out: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    vol = np.median(np.exp(r.result.g / 2), axis=0)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    x = np.arange(len(r.dates))
    for i, n in enumerate(r.names):
        ax.plot(x, vol[:, i], label=n, color=COLORS[i % 4] if i < 4 else None)
    ticks = x[:: max(1, len(x) // 6)]
    ax.set_xticks(ticks, [r.dates[t] for t in ticks], fontsize=7)
    ax.set_ylabel("structural s.d. (posterior median)")
    ax.legend(fontsize=7)
    files["vol"] = _save(fig, out, "m3_volatility.png")
    pairs = [(a, b) for a, b in pairs if a in r.names and b in r.names]
    if pairs:
        h = np.arange(r.irfs.shape[2])
        fig, axes = plt.subplots(1, len(pairs), figsize=(4 * len(pairs), 3.2), squeeze=False)
        for ax, (resp, shock) in zip(axes[0], pairs, strict=True):
            i, j = r.names.index(resp), r.names.index(shock)
            for di, d in enumerate(r.irf_dates):
                draws = r.irfs[di, :, :, i, j]
                c = COLORS[di % 4]
                ax.plot(h, np.median(draws, axis=0), color=c, label=d)
                lo, hi = np.quantile(draws, [0.16, 0.84], axis=0)
                ax.fill_between(h, lo, hi, color=c, alpha=0.12)
            ax.axhline(0, color="black", lw=0.5)
            ax.set_title(f"{resp} to {shock}", fontsize=9)
            ax.set_xlabel("months")
        axes[0][0].legend(fontsize=7)
        files["m3irf"] = _save(fig, out, "m3_irf.png")
    return files
