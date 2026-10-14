"""Matplotlib figures for screen and SVAR outputs. Returns the file names written."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from csuf_fullerton.core.svar.model import SvarResult
from csuf_fullerton.core.svar.screening import ScreenResult

BLUE = "#2a6f97"
GREY = "#8d99ae"


def granger_heatmap(r: ScreenResult, out: Path) -> str:
    names = r.theory.names
    k = len(names)
    m = np.where(np.eye(k, dtype=bool), np.nan, r.granger_p_adj)
    fig, ax = plt.subplots(figsize=(1 + 0.8 * k, 0.8 + 0.7 * k))
    im = ax.imshow(-np.log10(np.clip(m, 1e-6, 1)), cmap="Blues", vmin=0, vmax=4)
    ax.set_xticks(range(k), names, rotation=45, ha="right")
    ax.set_yticks(range(k), names)
    ax.set_xlabel("cause")
    ax.set_ylabel("effect (equation)")
    for i in range(k):
        for j in range(k):
            if i != j:
                ax.text(
                    j,
                    i,
                    f"{m[i, j]:.2f}",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white" if m[i, j] < 0.01 else "black",
                )
    fig.colorbar(im, ax=ax, label="-log10 Holm p")
    ax.set_title("Lag-augmented Granger tests")
    fig.tight_layout()
    name = "granger.png"
    fig.savefig(out / name, dpi=150)
    plt.close(fig)
    return name


def robustness_plot(r: ScreenResult, out: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    rec = r.recommended
    if rec is None:
        return files
    survivors = [c for c in r.ranked if c.verdict != "rejected"]
    for h in r.theory.headlines:
        key = (h.response, h.shock)
        fig, ax = plt.subplots(figsize=(6.5, 3.6))
        for c in survivors:
            if c is rec:
                continue
            ax.plot(c.headline_irf[key], color=GREY, lw=0.9, alpha=0.7)
        for v in r.ordering_irfs.values():
            ax.plot(v[key], color=GREY, lw=0.9, ls="--", alpha=0.9)
        ax.plot(
            rec.headline_irf[key],
            color=BLUE,
            lw=2.2,
            label="recommended {" + ", ".join(rec.spec.foreign) + "}",
        )
        ax.axhline(0, color="black", lw=0.6)
        ax.set_xlabel("months after shock")
        ax.set_title(f"{h.response} to a one-s.d. {h.shock} shock, all surviving specifications")
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        name = f"robust_{h.response}_{h.shock}.png"
        fig.savefig(out / name, dpi=150)
        plt.close(fig)
        files[f"robust_{h.response}_{h.shock}"] = name
    return files


def irf_grid(r: SvarResult, out: Path, scale: dict[str, float] | None = None) -> str:
    names = r.names
    nf = len(r.settings.foreign)
    shocks = list(range(nf))
    resp = list(range(nf, len(names)))
    sc = scale or {}
    b = r.bands
    fig, axes = plt.subplots(
        len(resp),
        len(shocks),
        figsize=(2.6 * len(shocks), 1.9 * len(resp)),
        sharex=True,
        squeeze=False,
    )
    for a, i in enumerate(resp):
        f = sc.get(names[i], 1.0)
        for c, j in enumerate(shocks):
            ax = axes[a][c]
            ax.fill_between(
                range(b.point.shape[0]),
                f * b.lower[:, i, j],
                f * b.upper[:, i, j],
                color=BLUE,
                alpha=0.2,
                lw=0,
            )
            ax.plot(f * b.point[:, i, j], color=BLUE, lw=1.6)
            ax.axhline(0, color="black", lw=0.5)
            if a == 0:
                ax.set_title(f"{names[j]} shock", fontsize=9)
            if c == 0:
                ax.set_ylabel(names[i], fontsize=9)
            ax.tick_params(labelsize=7)
    fig.suptitle(
        f"Domestic responses to foreign shocks ({b.level:.0%} bootstrap bands)", fontsize=10
    )
    fig.tight_layout()
    name = "irf.png"
    fig.savefig(out / name, dpi=150)
    plt.close(fig)
    return name
